(() => {
  const esc = (s='') => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const inline = (s='') => {
    let x = esc(s);
    x = x.replace(/`([^`]+)`/g,'<code>$1</code>');
    x = x.replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>');
    x = x.replace(/\*([^*]+)\*/g,'<em>$1</em>');
    x = x.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)&quot;&lt;&gt;]+|(?:\.\.?\/|\/)[^\s)&quot;&lt;&gt;]+)\)/g,'<a href="$2" rel="noreferrer noopener">$1</a>');
    x = x.replace(/&lt;p class=&quot;aura-beat&quot;&gt;([\s\S]*?)&lt;\/p&gt;/g,'<p class="aura-beat">$1</p>');
    return x;
  };
  const slug = (s='section') => s.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'') || 'section';

  function render(md, options={}){
    const lines = String(md || '').replace(/\r/g,'').split('\n');
    let html = '', i = 0;
    const headings = [];
    while (i < lines.length){
      let l = lines[i];
      if (!l.trim()){ i++; continue; }
      if (/^---+$/.test(l.trim()) || /^\* \* \*$/.test(l.trim())){ html += '<hr>'; i++; continue; }
      const h = l.match(/^(#{1,4})\s+(.+)$/);
      if (h){
        const level = h[1].length;
        const text = h[2].trim();
        if (options.skipH1 && level === 1){ i++; continue; }
        const id = `${slug(text)}-${i}`;
        html += `<h${level} id="${id}">${inline(text)}</h${level}>`;
        headings.push({id,text,level}); i++; continue;
      }
      if (l.startsWith('>')){
        const buf=[];
        while(i<lines.length && lines[i].startsWith('>')){ buf.push(lines[i].replace(/^>\s?/,'')); i++; }
        html += `<blockquote><p>${buf.map(v=>inline(v)).join('<br>')}</p></blockquote>`; continue;
      }
      if (/^[-*]\s+/.test(l)){
        const items=[];
        while(i<lines.length && /^[-*]\s+/.test(lines[i])){ items.push(lines[i].replace(/^[-*]\s+/,'')); i++; }
        html += `<ul>${items.map(v=>`<li>${inline(v)}</li>`).join('')}</ul>`; continue;
      }
      if (/^\d+\.\s+/.test(l)){
        const items=[];
        while(i<lines.length && /^\d+\.\s+/.test(lines[i])){ items.push(lines[i].replace(/^\d+\.\s+/,'')); i++; }
        html += `<ol>${items.map(v=>`<li>${inline(v)}</li>`).join('')}</ol>`; continue;
      }
      if (/^<p class="aura-beat">[\s\S]*<\/p>$/.test(l.trim())){
        html += l.trim(); i++; continue;
      }
      const buf=[];
      while(i<lines.length && lines[i].trim() && !/^(#{1,4})\s+/.test(lines[i]) && !/^---+$/.test(lines[i].trim()) && !/^\* \* \*$/.test(lines[i].trim()) && !lines[i].startsWith('>') && !/^[-*]\s+/.test(lines[i]) && !/^\d+\.\s+/.test(lines[i]) && !/^<p class="aura-beat">/.test(lines[i].trim())){
        buf.push(lines[i].trim()); i++;
      }
      html += `<p>${inline(buf.join(' '))}</p>`;
    }
    return { html, headings };
  }
  window.BLReaderMarkdown = { render, esc, slug };
})();
