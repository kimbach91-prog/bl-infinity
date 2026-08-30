(()=>{
  const links=[...document.querySelectorAll('a[href^="#"]')];
  for(const a of links)a.addEventListener('click',()=>history.replaceState(null,'',a.getAttribute('href')));

  const nav=document.querySelector('.top nav');
  if(!nav||nav.querySelector('a[href$="academic-democracy.html"]'))return;
  const theory=nav.querySelector('a[href$="theory.html"]');
  if(!theory)return;
  const href=theory.getAttribute('href').replace(/theory\.html$/, 'academic-democracy.html');
  const a=document.createElement('a');
  a.href=href;
  a.textContent='Dân chủ Học thuật';
  theory.insertAdjacentElement('afterend',a);
})();
