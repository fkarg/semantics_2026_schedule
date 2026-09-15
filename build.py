#!/usr/bin/env python3
"""Import the official public programme and generate a browsable static copy."""
import argparse
from datetime import datetime, timezone
import hashlib
from html import escape
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unicodedata
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET
import zipfile

from bs4 import BeautifulSoup
import markdown

ROOT = Path(__file__).resolve().parent
BASE = 'https://2026-eu.semantics.cc/'
WORKBOOK = 'https://docs.google.com/spreadsheets/d/1LUhUeGu-op2PES1YuhkJGS4--v87Emu2tTeO-o_tM0g/export?format=xlsx'
NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
      'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
DAYS = {'2026-09-15': ('Tuesday', '15 September', 'Pre-conference'),
        '2026-09-16': ('Wednesday', '16 September', 'Conference day 1'),
        '2026-09-17': ('Thursday', '17 September', 'Conference day 2')}


def workbook_sheets(path):
    with zipfile.ZipFile(path) as archive:
        strings = [''.join(t.text or '' for t in item.findall('.//s:t', NS))
                   for item in ET.fromstring(archive.read('xl/sharedStrings.xml'))]
        for i, day in enumerate(DAYS, 1):
            root = ET.fromstring(archive.read(f'xl/worksheets/sheet{i}.xml'))
            cells = {}
            for cell in root.findall('.//s:c', NS):
                value = cell.find('s:v', NS)
                if value is not None:
                    cells[cell.get('r')] = strings[int(value.text)] if cell.get('t') == 's' else value.text
                elif cell.get('t') == 'inlineStr':
                    cells[cell.get('r')] = ''.join(t.text or '' for t in cell.findall('.//s:t', NS))
            merges = [c.get('ref') for c in root.findall('.//s:mergeCell', NS)]
            yield day, cells, merges


def document_paragraphs(path):
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read('word/document.xml'))
    paragraphs = []
    for p in root.findall('.//w:p', NS):
        text = ''.join(t.text or '' for t in p.findall('.//w:t', NS)).strip()
        if text:
            style = p.find('w:pPr/w:pStyle', NS)
            paragraphs.append((text, style.get('{'+NS['w']+'}val', '') if style is not None else ''))
    return paragraphs


def document_talks(paragraphs):
    # Real documents contain both styled and unstyled talk titles. An abstract
    # label following a paragraph is an additional, unambiguous title boundary.
    starts = []
    for i, (text, style) in enumerate(paragraphs):
        if text.lower() == 'talks':
            continue
        next_abstract = i + 1 < len(paragraphs) and paragraphs[i + 1][0].startswith('Abstract:')
        if style == 'Heading2' or next_abstract:
            starts.append(i)
    talks = []
    for j, start in enumerate(starts):
        block = paragraphs[start + 1: starts[j + 1] if j + 1 < len(starts) else len(paragraphs)]
        abstract, speaker, track, collecting = [], '', '', False
        for text, _ in block:
            if text.startswith('Abstract:'):
                collecting = True
                abstract.append(text.partition(':')[2].strip())
            elif re.match(r'Speaker(?:\(s\))?:', text):
                speaker = text.partition(':')[2].strip()
                collecting = False
            elif text.startswith('Track:') or text == 'Sponsor Talk':
                track = text.partition(':')[2].strip() if ':' in text else text
                collecting = False
            elif collecting:
                abstract.append(text)
        title = re.sub(r'^Title:\s*', '', paragraphs[start][0])
        joined = '\n\n'.join(abstract)
        if joined.upper() in {'TBA', 'TBD', 'N/A'}:
            joined = ''
        # A heading in a descriptive interactive session isn't itself a talk.
        if abstract or speaker:
            talks.append(dict(title=title, speaker=speaker, abstract=joined, track=track))
    return talks


def normalized(text):
    return ''.join(c for c in unicodedata.normalize('NFKC', text).casefold() if c.isalnum())


def safe_html(source):
    soup = BeautifulSoup(source, 'html.parser')
    allowed = {'p', 'br', 'strong', 'em', 'b', 'i', 'ul', 'ol', 'li', 'a', 'h2', 'h3', 'h4', 'blockquote', 'code'}
    for tag in list(soup.find_all(True)):
        if tag.name in {'script', 'style', 'iframe', 'object'}:
            tag.decompose()
        elif tag.name not in allowed:
            tag.unwrap()
        else:
            href = urljoin(BASE, tag.get('href', '')) if tag.name == 'a' else ''
            tag.attrs = {}
            if href and urlparse(href).scheme in {'https', 'http', 'mailto'}:
                tag['href'] = href
    return str(soup)


def load_programme(sources):
    workshops = BeautifulSoup((sources / 'workshops.md').read_text(), 'html.parser')
    interactive = (sources / 'interactive.md').read_text()
    sessions = []
    for day, cells, merges in workbook_sheets(sources / 'programme.xlsx'):
        merged = {m.split(':')[0]: m.split(':')[-1] for m in merges}
        room_columns = [re.match(r'[A-Z]+', address).group() for address in cells
                        if re.fullmatch(r'[B-Z]1', address)]
        room_order = [cells[c+'1'].strip() for c in room_columns]
        for address, raw in cells.items():
            column, row = re.fullmatch(r'([A-Z]+)(\d+)', address).groups()
            if column == 'A' or row == '1' or not raw.strip():
                continue
            fields, listed_talks, notes = {}, [], []
            speaker = ''
            for line in raw.splitlines():
                line = re.sub(r'</?br\s*/?>', '', line, flags=re.I).strip()
                if not line:
                    continue
                key, sep, value = line.partition(':')
                key, value = key.strip().lower(), value.strip()
                if key == 'talk speaker':
                    speaker = ' '.join(filter(None, [speaker, value]))
                elif key == 'talk title':
                    listed_talks.append(dict(title=value, speaker=speaker, abstract='', track=''))
                    speaker = ''
                elif sep and key in {'group', 'slot title', 'title', 'chair', 'chairs', 'link'}:
                    fields[key] = value
                else:
                    notes.append(line)
            if speaker:
                notes.insert(0, speaker)
            groups = [g.strip().lower() for g in fields.get('group', '').split('|') if g.strip()]
            link = fields.get('link', '')
            title = fields.get('title') or fields.get('slot title') or (notes[0] if notes else 'Programme event')
            if title == 'Interactive Session':
                title = fields.get('slot title') or title
            time = cells['A'+row].strip()
            if address in merged:
                end_row = re.search(r'\d+', merged[address]).group()
                if end_row != row:
                    time = time.split('-')[0] + '-' + cells['A'+end_row].split('-')[-1]
            time = re.sub(r'\s*-\s*', ' – ', time).strip()
            end_column = re.match('[A-Z]+', merged.get(address, address)).group()
            room = cells.get(column+'1', '').strip() if end_column == column else ''
            session = dict(id=f'{day}-{address.lower()}', day=day, time=time, room=room,
                           column=room_columns.index(column), room_order=room_order,
                           colspan=room_columns.index(end_column)-room_columns.index(column)+1,
                           title=title, label=fields.get('slot title', ''), groups=groups,
                           chair=fields.get('chair', fields.get('chairs', '')),
                           talks=listed_talks, description='', source='', source_time='',
                           time_conflict=False, notes=notes)
            if link and not link.startswith('http'):
                paragraphs = document_paragraphs(sources / (link+'.docx'))
                docs = document_talks(paragraphs)
                by_title = {normalized(t['title']): t for t in docs}
                if listed_talks:
                    for talk in listed_talks:
                        key = normalized(talk['title'])
                        if key not in by_title:
                            raise ValueError(f'No abstract document match for {talk["title"]}')
                        match = by_title[key]
                        talk.update(abstract=match['abstract'], track=match['track'])
                else:
                    session['talks'] = docs
                session['source_time'] = next((t for t, _ in paragraphs if t.startswith('Time:')), '')
                source_times = re.findall(r'\b(\d{1,2}):(\d{2})', session['source_time'])
                sheet_times = re.findall(r'\b(\d{1,2}):(\d{2})', time)
                session['time_conflict'] = bool(source_times) and [(int(h), m) for h, m in source_times] != [(int(h), m) for h, m in sheet_times]
                page = 'speakers' if set(groups) & {'keynote', 'invited_talk'} else 'sessions'
                session['source'] = BASE+'page/'+page+'?page='+link
                session['document'] = 'https://docs.google.com/document/d/'+link+'/edit'
                if not session['talks']:
                    session['description'] = ''.join('<p>'+escape(t)+'</p>' for t, _ in paragraphs if not t.startswith(('Time:', 'Chair:', 'Session ')))
            elif link:
                session['source'] = link
                fragment = urlparse(link).fragment
                if 'accepted_workshops_tutorials' in link:
                    item = workshops.find(id=fragment)
                    if item is None:
                        raise ValueError(f'Missing workshop {fragment}')
                    session['description'] = safe_html(str(item))
                elif 'interactive_sessions' in link:
                    parts = re.split(r'<div id="([^"]+)"></div>', interactive)
                    section = parts[parts.index(fragment)+1]
                    session['description'] = safe_html(markdown.markdown(section))
            for talk in session['talks']:
                identity = (link or session['id']) + '\0' + normalized(talk['title'])
                talk['id'] = hashlib.sha256(identity.encode()).hexdigest()[:16]
            sessions.append(session)
    return sessions


def paragraphs(text):
    return ''.join('<p>'+escape(p)+'</p>' for p in text.split('\n\n') if p)


def abstract_html(talk):
    return paragraphs(talk['abstract']) if talk['abstract'] else '<p class="muted">Abstract not yet published in the source.</p>'


def metadata(session):
    return escape(session['time']+' CEST'+(' · '+session['room'] if session['room'] else ''))


def document(title, body, prefix, stamp):
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)} · SEMANTiCS 2026</title><link rel="stylesheet" href="{prefix}style.css">
<script defer src="{prefix}app.js"></script></head><body>
<header class="masthead"><a class="brand" href="{prefix}index.html">SEMANT<span>i</span>CS <span class="year">2026</span></a><span class="edition">Your local programme</span>
<a class="original" href="{BASE}page/programme" target="_blank" rel="noopener">Official programme ↗</a></header>
{body}<footer>Local snapshot · {escape(stamp)} · All times CEST (Ghent).<br>
Times and rooms follow the official timetable. Source documents can contain older times.</footer></body></html>'''


def source_links(session):
    links = []
    if session['source']:
        links.append(f'<a href="{escape(session["source"], quote=True)}" target="_blank" rel="noopener">Official details ↗</a>')
    if session.get('document'):
        links.append(f'<a href="{escape(session["document"], quote=True)}" target="_blank" rel="noopener">Source document ↗</a>')
    return '<div class="source-links">'+' · '.join(links)+'</div>' if links else ''


def session_details(session):
    content = ''
    if session['chair']:
        content += '<p class="chair">Chair: '+escape(session['chair'])+'</p>'
    if session['notes']:
        content += '<div class="notes">'+safe_html(markdown.markdown('\n\n'.join(session['notes'])))+'</div>'
    if session['time_conflict']:
        content += '<p class="notice">The source document lists a different time ('+escape(session['source_time'].removeprefix('Time: '))+'). The time above follows the programme timetable.</p>'
    return content


def build_site(sessions, destination, stamp):
    destination.mkdir(parents=True, exist_ok=True)
    for sub in ('sessions', 'talks'):
        (destination / sub).mkdir(exist_ok=True)
    for asset in ('style.css', 'app.js'):
        shutil.copyfile(ROOT / asset, destination / asset)
    for session in sessions:
        session_path = f'sessions/{session["id"]}.html'
        talk_items = ''
        for talk in session['talks']:
            talk_items += f'<article class="talk"><h3><a class="talk-title" href="../talks/{talk["id"]}.html">{escape(talk["title"])}</a></h3><p class="speaker">{escape(talk["speaker"])}</p><div class="abstract">{abstract_html(talk)}</div></article>'
            body = f'''<main class="detail-page"><nav class="breadcrumbs"><a href="../index.html?day={session['day']}#{session['id']}">Programme</a><span>/</span><a href="../{session_path}">{escape(session['title'])}</a></nav>
<p class="eyebrow">{DAYS[session['day']][0]} · {DAYS[session['day']][1]} · {escape(talk['track'] or session['label'])}</p>
<h1>{escape(talk['title'])}</h1><p class="detail-speaker">{escape(talk['speaker'])}</p>
<p class="detail-meta">{metadata(session)}</p><p class="muted">Session time; individual talk times are not specified in the timetable.</p>
{session_details(session)}<section class="abstract"><h2>Abstract</h2>{abstract_html(talk)}</section>{source_links(session)}</main>'''
            (destination / 'talks' / (talk['id']+'.html')).write_text(document(talk['title'], body, '../', stamp))
        body = f'''<main class="detail-page"><nav class="breadcrumbs"><a href="../index.html?day={session['day']}#{session['id']}">← Back to programme</a></nav>
<p class="eyebrow">{DAYS[session['day']][0]} · {DAYS[session['day']][1]} · {escape(session['label'])}</p><h1>{escape(session['title'])}</h1>
<p class="detail-meta">{metadata(session)}</p>{session_details(session)}<div class="description">{session['description']}</div>{talk_items}{source_links(session)}</main>'''
        (destination / session_path).write_text(document(session['title'], body, '../', stamp))
    rooms = sorted({s['room'] for s in sessions if s['room']})
    body = f'''<main class="programme"><section class="toolbar" aria-label="Programme filters"><nav class="days" aria-label="Conference day">'''
    for day, (_, date, label) in DAYS.items():
        body += f'<a href="index.html?day={day}" data-day="{day}">{date[:2]} Sept <small>{label}</small></a>'
    body += '<a href="index.html?day=all" data-day="">All days</a></nav>'
    body += '<div class="filter-row"><label class="search-label"><span class="sr-only">Search programme</span><input id="search" type="search" placeholder="Search talks, speakers, topics…" autocomplete="off"></label><label><span class="sr-only">Room</span><select id="room"><option value="">All rooms</option>'
    body += ''.join(f'<option>{escape(room)}</option>' for room in rooms)
    body += '</select></label><label class="selected-filter" hidden><input id="selected-only" type="checkbox">Selected only <span id="selected-count"></span></label><button id="clear" type="button">Clear</button><p id="result-count" role="status" aria-live="polite"></p></div></section><p id="storage-notice" role="status" hidden>This browser cannot save favourites. Your selections will last only while this page stays open.</p><noscript><p>All days are shown. Browser Find works without JavaScript.</p></noscript><p id="empty" hidden>No matching sessions. Try another search or clear the filters.</p>'
    for day, (weekday, date, label) in DAYS.items():
        body += f'<section class="day" data-day="{day}"><header class="day-heading"><h1>{weekday}, {date} <span>· {label}</span></h1><p>CEST · Titles open as normal links · Expand abstracts in place</p></header>'
        day_sessions = [s for s in sessions if s['day'] == day]
        day_rooms = day_sessions[0]['room_order']
        body += f'<div class="timetable-wrap" tabindex="0" role="region" aria-label="{weekday} timetable, scroll for more rooms and times"><table class="timetable" style="--room-count:{len(day_rooms)}"><thead><tr><th scope="col" class="time-cell">Time · CEST</th>'
        body += ''.join('<th scope="col" data-room="'+escape(room, quote=True)+'">'+escape(room)+'</th>' for room in day_rooms)
        body += '</tr></thead><tbody>'
        times = list(dict.fromkeys(s['time'] for s in day_sessions))
        for time in times:
            body += '<tr class="time-group" data-time="'+escape(time, quote=True)+'"><th scope="row" class="time-cell"><div class="time-label">'+escape(time).replace(' – ', '<span>–</span>')+'</div></th>'
            row_sessions = {s['column']: s for s in day_sessions if s['time'] == time}
            col = 0
            while col < len(day_rooms):
                session = row_sessions.get(col)
                if session is None:
                    body += '<td class="empty-cell"></td>'
                    col += 1
                    continue
                meaningful = bool(session['groups']) and not set(session['groups']) & {'arrival', 'break', 'extra'}
                search = ' '.join([session['title'], session['label'], session['chair'], session['room'], *session['groups'], *session['notes'], BeautifulSoup(session['description'], 'html.parser').get_text(' ')] + [' '.join([t['title'], t['speaker'], t['abstract'], t['track']]) for t in session['talks']])
                search = ' '.join(search.split())
                # Source content, not spreadsheet coordinates: row insertion must not
                # silently move a favourite to a different session.
                identity = [session['day'], session['time'], session['room'], session['source'] or session['title']]
                favourite_id = hashlib.sha256(json.dumps(identity).encode()).hexdigest()[:16]
                body += f'<td data-column="{col}" colspan="{session["colspan"]}" class="event-cell" data-room="{escape(session["room"], quote=True)}"><article id="{session["id"]}" class="session{" compact" if not meaningful else ""}" data-room="{escape(session["room"], quote=True)}" data-search="{escape(search, quote=True)}"><div class="card-kicker">{escape(session["label"] or "Programme")}</div><div class="session-heading"><h2 class="session-title"><a href="sessions/{session["id"]}.html">{escape(session["title"])}</a></h2>'
                if session['room']:
                    body += f'<button class="favourite" data-favourite-id="{favourite_id}" type="button" aria-pressed="false" aria-label="Favourite session: {escape(session["title"], quote=True)}" title="Favourite this session" hidden>☆</button>'
                body += '</div>'
                if session['chair']:
                    body += '<p class="chair">Chair: '+escape(session['chair'])+'</p>'
                for talk in session['talks']:
                    body += f'<article class="talk"><h3><a class="talk-title" href="talks/{talk["id"]}.html">{escape(talk["title"])}</a></h3><p class="speaker" title="{escape(talk["speaker"], quote=True)}">{escape(talk["speaker"])}</p><details><summary>Abstract</summary><div class="abstract">{abstract_html(talk)}</div><a class="read-link" href="talks/{talk["id"]}.html">Open talk page →</a></details></article>'
                if session['description']:
                    body += '<details class="session-description"><summary>Session details</summary><div class="description">'+session['description']+'</div></details>'
                display_notes = [note for note in session['notes'] if note != session['title'] and not note.startswith('[Online room]')]
                if display_notes:
                    body += '<div class="notes">'+safe_html(markdown.markdown('\n\n'.join(display_notes)))+'</div>'
                body += '</article></td>'
                col += session['colspan']
            body += '</tr>'
        body += '</tbody></table></div></section>'
    body += '</main>'
    (destination / 'index.html').write_text(document('Programme', body, '', stamp))
    (destination / 'programme.json').write_text(json.dumps(sessions, ensure_ascii=False, indent=2))


def refresh(sources):
    # Download an entire snapshot before replacing the previous cache.
    with tempfile.TemporaryDirectory(dir=ROOT, prefix='.refresh-') as folder:
        cache = Path(folder)
        downloads = {'programme.xlsx': WORKBOOK,
                     'workshops.md': BASE+'content/accepted_workshops_tutorials.md',
                     'interactive.md': BASE+'content/interactive_sessions.md'}
        for filename, url in downloads.items():
            subprocess.run(['curl', '-fLsS', url, '-o', str(cache / filename)], check=True)
        links = set()
        for _, cells, _ in workbook_sheets(cache / 'programme.xlsx'):
            for value in cells.values():
                links.update(re.findall(r'^Link:\s*([A-Za-z0-9_-]+)\s*$', value, re.M))
        for i, link in enumerate(sorted(links), 1):
            print(f'Downloading document {i}/{len(links)}', flush=True)
            subprocess.run(['curl', '-fLsS', f'https://docs.google.com/document/d/{link}/export?format=docx', '-o', str(cache / (link+'.docx'))], check=True)
        load_programme(cache)
        (cache / 'snapshot.json').write_text(json.dumps({'fetched_at': datetime.now(timezone.utc).isoformat(timespec='seconds'), 'programme_url': BASE+'page/programme', 'workbook_url': WORKBOOK}, indent=2))
        sources.mkdir(exist_ok=True)
        for path in cache.iterdir():
            shutil.copyfile(path, sources / path.name)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true', help='Download a fresh public programme snapshot first')
    args = parser.parse_args()
    sources = ROOT / 'sources'
    if args.refresh:
        refresh(sources)
    sessions = load_programme(sources)
    stamp = json.loads((sources / 'snapshot.json').read_text())['fetched_at']
    build_site(sessions, ROOT / 'site', stamp)
    print(f'Built {len(sessions)} programme entries and {sum(len(s["talks"]) for s in sessions)} talks: {ROOT / "site/index.html"}')
