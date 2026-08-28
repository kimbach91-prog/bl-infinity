(()=>{const links=[...document.querySelectorAll('a[href^="#"]')];for(const a of links)a.addEventListener('click',()=>history.replaceState(null,'',a.getAttribute('href')));})();
