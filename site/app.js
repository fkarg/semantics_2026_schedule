// Progressive enhancement only: links and disclosures remain browser-native.
const search = document.querySelector('#search');
if (search) {
  const room = document.querySelector('#room');
  const selectedOnly = document.querySelector('#selected-only');
  const exportCalendar = document.querySelector('#export-calendar');
  exportCalendar.parentElement.hidden = false;
  const storagePrefix = 'semantics2026:favourite:';
  let canSave = true;
  const params = new URLSearchParams(location.search);
  const validDays = [...document.querySelectorAll('.day')].map(day => day.dataset.day);
  const selectedDay = params.get('day') === 'all' ? '' :
    validDays.includes(params.get('day')) ? params.get('day') : validDays[0];
  search.value = params.get('q') || '';
  room.value = params.get('room') || '';
  selectedOnly.checked = params.get('selected') === '1';
  selectedOnly.closest('label').hidden = false;
  if (room.selectedIndex < 0) room.value = '';
  const normalize = text => text.normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase();
  const entries = [...document.querySelectorAll('.session')].map(element => ({
    element, text: normalize(element.dataset.search), day: element.closest('.day').dataset.day,
    button: element.querySelector('.favourite'), selected: false
  }));
  // Retain original coordinates and spans so toggling the view is reversible.
  const tables = [...document.querySelectorAll('.timetable')].map(table => {
    const headers = [...table.tHead.rows[0].cells].slice(1).map(cell => ({cell, title: cell.textContent}));
    const cells = [];
    for (const row of table.tBodies[0].rows) {
      let column = 0;
      for (const cell of row.querySelectorAll('td')) {
        cells.push({cell, column, span: cell.colSpan, session: cell.querySelector('.session')});
        column += cell.colSpan;
      }
    }
    return {table, headers, cells};
  });
  const clockFormat = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Europe/Brussels', year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23'
  });
  const timeRows = [...document.querySelectorAll('.time-group')].map(row => {
    const [start, end] = row.dataset.time.split('–').map(value => {
      if (!value.trim()) return null;
      const [hour, minute] = value.trim().split(':').map(Number);
      return hour * 60 + minute;
    });
    const label = document.createElement('div');
    label.className = 'now-label';
    label.hidden = true;
    row.querySelector('.time-cell').append(label);
    return {row, label, start, end, day: row.closest('.day').dataset.day};
  });
  function updateNow() {
    const parts = Object.fromEntries(clockFormat.formatToParts(new Date()).map(part => [part.type, part.value]));
    const today = `${parts.year}-${parts.month}-${parts.day}`;
    const minute = Number(parts.hour) * 60 + Number(parts.minute) + Number(parts.second) / 60;
    for (const {row, label, start, end, day} of timeRows) {
      const current = day === today && minute >= start && (end === null || minute < end);
      row.classList.toggle('is-now', current);
      label.hidden = !current;
      if (current) {
        // Content determines row height; elapsed time determines position within it.
        const progress = end === null ? 0 : (minute - start) / (end - start);
        row.style.setProperty('--now-position', `${progress * 100}%`);
        label.textContent = `Now ${parts.hour}:${parts.minute}`;
      }
    }
  }
  updateNow();
  setInterval(updateNow, 15000);
  window.addEventListener('focus', updateNow);
  window.addEventListener('pageshow', updateNow);
  document.addEventListener('visibilitychange', updateNow);
  function readSelection() {
    if (canSave) {
      try {
        for (const entry of entries) {
          entry.selected = Boolean(entry.button && localStorage.getItem(storagePrefix + entry.button.dataset.favouriteId) === '1');
        }
      } catch {
        canSave = false;
        document.querySelector('#storage-notice').hidden = false;
      }
    }
    filter();
  }
  for (const entry of entries) {
    if (!entry.button) continue;
    entry.button.hidden = false;
    entry.button.addEventListener('click', () => {
      entry.selected = !entry.selected;
      if (canSave) {
        try {
          const key = storagePrefix + entry.button.dataset.favouriteId;
          if (entry.selected) localStorage.setItem(key, '1');
          else localStorage.removeItem(key);
        } catch {
          canSave = false;
          document.querySelector('#storage-notice').hidden = false;
        }
      }
      filter();
    });
  }
  exportCalendar.addEventListener('click', () => {
    const text = value => value.replace(/\\/g, '\\\\').replace(/\r\n|\r|\n/g, '\\n')
      .replace(/;/g, '\\;').replace(/,/g, '\\,');
    const stamp = new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d{3}Z$/, 'Z');
    const lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//SEMANTiCS 2026 personal programme//EN'];
    for (const {button, selected} of entries) {
      if (!selected) continue;
      const event = JSON.parse(button.dataset.calendar);
      lines.push('BEGIN:VEVENT', `UID:${button.dataset.favouriteId}@semantics-2026.fkarg.me`,
        `DTSTAMP:${stamp}`, `DTSTART:${event.start}`, `DTEND:${event.end}`,
        `SUMMARY:${text(event.title)}`, `LOCATION:${text(event.location)}`,
        `DESCRIPTION:${text(event.description)}`, `URL:${event.url}`, 'END:VEVENT');
    }
    lines.push('END:VCALENDAR');
    // RFC 5545 folds at 75 octets, including the continuation space.
    const encoder = new TextEncoder();
    const calendar = lines.map(line => {
      let folded = '', bytes = 0;
      for (const character of line) {
        const size = encoder.encode(character).length;
        if (bytes + size > 75) { folded += '\r\n '; bytes = 1; }
        folded += character;
        bytes += size;
      }
      return folded;
    }).join('\r\n') + '\r\n';
    const url = URL.createObjectURL(new Blob([calendar], {type: 'text/calendar;charset=utf-8'}));
    const link = document.createElement('a');
    link.href = url;
    link.download = 'semantics-2026-selected.ics';
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  });
  function filter() {
    const words = normalize(search.value).trim().split(/\s+/).filter(Boolean);
    let count = 0;
    let selectedCount = 0;
    for (const {element, text, day, button, selected} of entries) {
      if (button) {
        button.setAttribute('aria-pressed', String(selected));
        button.textContent = selected ? '★' : '☆';
        button.title = selected ? 'Remove from favourites' : 'Favourite this session';
      }
      element.classList.toggle('favourited', selected);
      const visible = (!selectedDay || selectedDay === day) &&
        (!room.value || !element.dataset.room || element.dataset.room === room.value) &&
        (!selectedOnly.checked || !element.dataset.room || selected) &&
        words.every(word => text.includes(word));
      element.hidden = !visible;
      count += Number(visible);
      selectedCount += Number(visible && selected);
    }
    for (const row of document.querySelectorAll('.time-group')) {
      row.classList.toggle('empty-slot', !row.querySelector('.session:not([hidden])'));
    }
    for (const day of document.querySelectorAll('.day')) {
      day.hidden = !day.querySelector('.session:not([hidden])');
    }
    for (const {table, headers, cells} of tables) {
      const active = cells.filter(({session}) => session && !session.hidden);
      const columns = new Set(active.filter(({session}) => session.dataset.room).map(({column}) => column));
      const compactRooms = selectedOnly.checked || Boolean(room.value);
      const sharedOnly = compactRooms && active.length > 0 && columns.size === 0;
      if (!compactRooms) headers.forEach((_, column) => columns.add(column));
      else if (!sharedOnly) {
        // A shared event must retain a cell even when none of its
        // original columns contain a selected room-specific session.
        for (const {column, span} of active) {
          if (![...columns].some(index => index >= column && index < column + span)) columns.add(column);
        }
      }
      headers.forEach(({cell, title}, column) => {
        cell.hidden = sharedOnly ? column !== 0 : !columns.has(column);
        cell.textContent = sharedOnly && column === 0 ? 'Shared events' : title;
        cell.dataset.room = sharedOnly ? '' : title;
      });
      for (const {cell, column, span, session} of cells) {
        const emptySharedSlot = cell.parentElement.classList.contains('empty-slot') && cell.cellIndex === 1;
        const visibleSpan = sharedOnly ? Number(Boolean(session && !session.hidden) || emptySharedSlot) :
          [...columns].filter(index => index >= column && index < column + span).length;
        cell.hidden = visibleSpan === 0;
        cell.colSpan = Math.max(1, visibleSpan);
        cell.classList.toggle('filtered-empty', Boolean(session && session.hidden));
      }
      table.style.setProperty('--room-count', String(sharedOnly ? 1 : Math.max(1, columns.size)));
    }
    document.querySelector('#empty').hidden = selectedOnly.checked ? selectedCount > 0 : count > 0;
    document.querySelector('#empty').textContent = selectedOnly.checked ?
      'No selected sessions match this view. Uncheck “Selected only” to browse and star sessions.' :
      'No matching sessions. Try another search or clear the filters.';
    document.querySelector('#selected-count').textContent = `(${entries.filter(entry => entry.selected).length})`;
    exportCalendar.disabled = !entries.some(entry => entry.selected);
    document.querySelector('#result-count').textContent = `${count} programme entries`;
    for (const link of document.querySelectorAll('.days a')) {
      if (link.dataset.day === selectedDay) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
      const query = new URLSearchParams();
      query.set('day', link.dataset.day || 'all');
      if (search.value) query.set('q', search.value);
      if (room.value) query.set('room', room.value);
      if (selectedOnly.checked) query.set('selected', '1');
      link.href = 'index.html' + (query.size ? '?' + query : '');
    }
  }
  search.addEventListener('input', filter);
  room.addEventListener('change', filter);
  selectedOnly.addEventListener('change', () => {
    const url = new URL(location.href);
    if (selectedOnly.checked) url.searchParams.set('selected', '1');
    else url.searchParams.delete('selected');
    history.replaceState(null, '', url);
    filter();
  });
  document.querySelector('#clear').addEventListener('click', () => {
    search.value = ''; room.value = ''; filter(); search.focus();
  });
  readSelection();
  // Recompute on back/forward cache restoration, preserving the browser's inputs.
  window.addEventListener('pageshow', readSelection);
  window.addEventListener('focus', readSelection);
  window.addEventListener('storage', event => {
    if (event.key === null || event.key.startsWith(storagePrefix)) readSelection();
  });
}
