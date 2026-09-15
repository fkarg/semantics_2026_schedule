"""Contract tests using the actual public programme snapshot."""
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from bs4 import BeautifulSoup
import build

SOURCES = Path(__file__).resolve().parents[1] / 'sources'


class ProgrammeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sessions = build.load_programme(SOURCES)

    def test_timetable_is_authority_for_time_and_room(self):
        session = next(s for s in self.sessions if s['title'] == 'Querying Knowledge Graphs')
        self.assertEqual((session['day'], session['time'], session['room']),
                         ('2026-09-16', '11:15 – 12:40', 'Concertzaal'))
        self.assertEqual(len(session['talks']), 4)
        self.assertIn('11:00', session['source_time'])
        self.assertTrue(session['time_conflict'])
        self.assertIn('KGXL-Query', session['talks'][0]['title'])
        self.assertIn('hybrid inference', session['talks'][0]['abstract'])

    def test_source_annotations_do_not_prevent_abstract_matching(self):
        talks = [t for s in self.sessions for t in s['talks']]
        talk = next(t for t in talks if t['title'].startswith('Start with the User'))
        self.assertIn('We were not semantic-data experts.', talk['abstract'])

    def test_unstyled_docx_title_is_not_lost_or_folded_into_previous_talk(self):
        session = next(s for s in self.sessions if s['title'] == 'From Semantic Foundations to AI Applications')
        self.assertEqual(len(session['talks']), 4)
        talk = next(t for t in session['talks'] if t['title'] == 'Classifying Classes in Wikidata')
        self.assertIn('six-way categorisation', talk['abstract'])
        self.assertEqual(talk['speaker'], 'Ege Atacan Doğan, JMU Würzburg')

    def test_keynote_abstract_keeps_all_paragraphs(self):
        talk = next(t for s in self.sessions for t in s['talks']
                    if t['title'] == 'How good are Large Language Models at Ontology Engineering?')
        self.assertIn('Large Language Models (LLMs)', talk['abstract'])
        self.assertIn('should LLMs merely assist ontology', talk['abstract'])

    def test_workshop_details_are_available_locally(self):
        session = next(s for s in self.sessions if s['title'] == 'Developers Workshop (SemDev)')
        self.assertIn('bridge between academia and industry', session['description'])
        self.assertIn('https://semantics2026.semdev.org/', session['description'])

    def test_merged_shared_events_do_not_claim_all_rooms(self):
        coffee = [s for s in self.sessions if s['title'].lower() == 'coffee break']
        # Workbook: B5/B9 on Tuesday, B5 on Wednesday, B4/B8 on Thursday.
        self.assertEqual(len(coffee), 5)
        self.assertTrue(all(s['room'] == '' for s in coffee))

    def test_missing_abstract_is_explicit(self):
        talk = next(t for s in self.sessions for t in s['talks'] if t['title'].startswith('Scar Tissue'))
        self.assertEqual(talk['abstract'], '')

    def test_posters_and_demos_event_keeps_both_source_labels(self):
        # Consecutive Talk speaker fields in B9 are event labels, not replacements.
        event = next(s for s in self.sessions if s['id'] == '2026-09-16-b9')
        self.assertEqual(event['title'], 'Posters and Demos Walk')

    def test_timetable_keeps_physical_rooms_and_shared_cell_spans(self):
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            build.build_site(self.sessions, site, '2026-09-14T20:00:00+00:00')
            soup = BeautifulSoup((site / 'index.html').read_text(), 'html.parser')
            day = soup.select_one('.day[data-day="2026-09-16"]')
            self.assertEqual([h.get_text(' ', strip=True) for h in day.select('thead th[scope=col]')],
                             ['Time · CEST', 'Concertzaal', 'Kraakhuis', 'Kabinet', 'Anatomisch Theater'])
            keynote = day.find(id='2026-09-16-b4')
            self.assertEqual(keynote.find_parent('td')['data-column'], '0')
            querying = day.find(id='2026-09-16-b6')
            buildings = day.find(id='2026-09-16-d6')
            self.assertEqual(querying.find_parent('tr'), buildings.find_parent('tr'))
            self.assertEqual(buildings.find_parent('td')['data-column'], '2')
            coffee = day.find(id='2026-09-16-b5')
            self.assertEqual(coffee.find_parent('td')['colspan'], '4')

    def test_favourites_identify_sessions_without_using_spreadsheet_row_numbers(self):
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            build.build_site(self.sessions, site, 'test')
            original = BeautifulSoup((site / 'index.html').read_text(), 'html.parser')
            keys = [b['data-favourite-id'] for b in original.select('.favourite')]
            self.assertEqual(len(keys), len(set(keys)))
            self.assertEqual(len(keys), sum(bool(s['room']) for s in self.sessions))
            for shared in original.select('.session[data-room=""]'):
                self.assertIsNone(shared.select_one('.favourite'))
            # A row inserted above the programme must not move stars to other events.
            moved = deepcopy(self.sessions)
            for session in moved:
                session['id'] += '-new-row'
            build.build_site(moved, site, 'test')
            updated = BeautifulSoup((site / 'index.html').read_text(), 'html.parser')
            self.assertEqual([b['data-favourite-id'] for b in updated.select('.favourite')], keys)

    def test_all_generated_local_links_resolve_and_abstracts_are_disclosures(self):
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            build.build_site(self.sessions, site, '2026-09-14T20:00:00+00:00')
            for page in site.rglob('*.html'):
                soup = BeautifulSoup(page.read_text(), 'html.parser')
                self.assertFalse(soup.select('[onclick]'))
                for a in soup.select('a[href]'):
                    href = a['href'].split('#')[0].split('?')[0]
                    if href and not href.startswith(('https:', 'http:', 'mailto:')):
                        self.assertTrue((page.parent / href).is_file(), (page, href))
            soup = BeautifulSoup((site / 'index.html').read_text(), 'html.parser')
            self.assertTrue(soup.select('details summary'))
            titles = soup.select('a.talk-title')
            self.assertEqual(len(titles), sum(len(s['talks']) for s in self.sessions))
            self.assertTrue(all(a['href'].startswith('talks/') for a in titles))


if __name__ == '__main__':
    unittest.main()
