// Progressive enhancement only: links and disclosures remain browser-native.
const search = document.querySelector('#search');
if (search) {
  const room = document.querySelector('#room');
  const params = new URLSearchParams(location.search);
  const validDays = [...document.querySelectorAll('.day')].map(day => day.dataset.day);
  const selectedDay = params.get('day') === 'all' ? '' :
    validDays.includes(params.get('day')) ? params.get('day') : validDays[0];
  search.value = params.get('q') || '';
  room.value = params.get('room') || '';
  if (room.selectedIndex < 0) room.value = '';
  const normalize = text => text.normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase();
  const entries = [...document.querySelectorAll('.session')].map(element => ({
    element, text: normalize(element.dataset.search), day: element.closest('.day').dataset.day
  }));
  function filter() {
    const words = normalize(search.value).trim().split(/\s+/).filter(Boolean);
    let count = 0;
    for (const {element, text, day} of entries) {
      const visible = (!selectedDay || selectedDay === day) &&
        (!room.value || !element.dataset.room || element.dataset.room === room.value) &&
        words.every(word => text.includes(word));
      element.hidden = !visible;
      count += Number(visible);
    }
    for (const group of document.querySelectorAll('.time-group, .day')) {
      group.hidden = !group.querySelector('.session:not([hidden])');
    }
    document.querySelector('#empty').hidden = count > 0;
    document.querySelector('#result-count').textContent = `${count} programme entries`;
    for (const link of document.querySelectorAll('.days a')) {
      if (link.dataset.day === selectedDay) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
      const query = new URLSearchParams();
      query.set('day', link.dataset.day || 'all');
      if (search.value) query.set('q', search.value);
      if (room.value) query.set('room', room.value);
      link.href = 'index.html' + (query.size ? '?' + query : '');
    }
  }
  search.addEventListener('input', filter);
  room.addEventListener('change', filter);
  document.querySelector('#clear').addEventListener('click', () => {
    search.value = ''; room.value = ''; filter(); search.focus();
  });
  filter();
  // Recompute on back/forward cache restoration, preserving the browser's inputs.
  window.addEventListener('pageshow', filter);
}
