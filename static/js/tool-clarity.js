/* Presentation only. Keep input IDs, values and processing handlers unchanged. */
(function () {
  'use strict';
  const t = window.ToolClarityCopy;
  const byId = id => document.getElementById(id);
  function copyNode(tag, key) {
    const node = document.createElement(tag);
    node.dataset.clarityCopy = key;
    node.textContent = t(key);
    return node;
  }
  function disclosure(key, id) {
    const details = document.createElement('details');
    details.className = 'tool-disclosure'; details.id = id;
    details.append(copyNode('summary', key));
    return details;
  }
  // Optional task entry: use the original tab buttons so lazy loading, access
  // checks and existing file state follow exactly the same navigation path.
  const topbar = document.querySelector('.main .topbar');
  if (topbar && byId('nav')) {
    const chooser = disclosure('taskTitle', 'toolTaskChooser');
    chooser.classList.add('tool-task-chooser');
    chooser.append(copyNode('p', 'taskHint'));
    const grid = document.createElement('div'); grid.className = 'tool-task-grid';
    [['process','taskProcess'],['builder','taskBuilder'],['compose','taskCompose'],
      ['download','taskDownload'],['upscale','taskUpscale'],['steam','taskSteam'],['da','taskDa']]
      .forEach(([target, key]) => {
        const tab = document.querySelector('#nav [data-tab="' + target + '"]');
        if (!tab) return;
        const button = copyNode('button', key);
        button.type = 'button'; button.dataset.taskTarget = target;
        button.addEventListener('click', () => {
          // Do not announce success or collapse until the lazy-loaded tab is
          // actually active. Its existing loader owns failures and retry.
          tab.click();
        });
        grid.append(button);
      });
    chooser.append(grid); topbar.after(chooser);
    const observer = new MutationObserver(records => {
      if (!chooser.open) return;
      const activated = records.some(record => record.target.classList.contains('active'));
      if (activated) {
        chooser.open = false;
        chooser.querySelector('summary').focus({preventScroll:true});
      }
    });
    document.querySelectorAll('[id^="tab-"]').forEach(pane => observer.observe(pane, {attributes:true, attributeFilter:['class']}));
    // Clicking the already active tool has no class mutation to observe.
    grid.addEventListener('click', event => {
      const target = event.target.closest('[data-task-target]')?.dataset.taskTarget;
      if (target && byId('tab-' + target)?.classList.contains('active')) {
        chooser.open = false;
        chooser.querySelector('summary').focus({preventScroll:true});
      }
    });
  }
  // Short outcomes remain visible; full explanations use the shared, keyboard-
  // and touch-accessible help control, not browser-only title attributes.
  ['compose','download','convert','upscale','hex','da'].forEach(name => {
    const pane = byId('tab-' + name);
    const heading = pane?.querySelector('h2');
    if (!heading) return;
    pane.classList.add('tool-clarity');
    const intro = copyNode('p', name); intro.className = 'tool-outcome';
    const anchor = heading.closest('.sm-help-heading') || heading;
    anchor.after(intro);
    const help = copyNode('p', name + 'Help');
    // Existing Character / Converter / HEX explanations remain on their
    // original question buttons. Give the outcome its own explanatory control.
    const existingHelp = anchor.querySelector('.sm-help__button');
    if (existingHelp) byId(existingHelp.getAttribute('aria-controls'))?.prepend(help);
    else window.WorkspaceHelp?.attach(help, intro);
  });

  const controls = document.querySelector('.compose-controls');
  if (controls) {
    controls.querySelector('.compose-intro')?.classList.add('clarity-superseded');
    const advanced = disclosure('optional', 'composeFineSettings');
    advanced.append(copyNode('p', 'defaults'));
    const backgroundRow = byId('composeChroma').closest('.row');
    const edges = document.createElement('div'); edges.className = 'row';
    ['composeTol','composeFeather'].forEach(id => edges.append(byId(id).closest('label')));
    advanced.append(edges);
    ['composeScale','composeOx','composeGifEncoder'].forEach(id => advanced.append(byId(id).closest('.row')));
    backgroundRow.after(advanced);
    backgroundRow.classList.add('tool-background-choice');
  }

  // Pick the source before choosing its destination format.
  const formatRow = byId('cvTarget')?.closest('.row');
  if (formatRow) byId('cvFileList').after(formatRow);
  const dlRow = byId('dlUrl')?.closest('.row');
  if (dlRow) {
    dlRow.classList.add('tool-download-fields');
    [['dlUrl','url'],['dlQuality','quality']].forEach(([id,key]) => {
      const input = byId(id), label = document.createElement('label');
      label.className = 'field'; label.htmlFor = id;
      input.before(label); label.append(copyNode('span', key), input);
    });
  }
  // These tools expose a download, not an in-memory file handoff. Be explicit
  // about the manual step; never fetch or upload the result just to navigate.
  ['dlLink','cvDl','upscaleDownload'].forEach(id => {
    const link = byId(id);
    if (!link) return;
    const next = document.createElement('div'); next.className = 'tool-next-step';
    next.append(copyNode('p', 'nextProcess'));
    const button = copyNode('button', 'openProcess'); button.type = 'button';
    button.addEventListener('click', () => document.querySelector('#nav [data-tab="process"]')?.click());
    next.append(button); link.after(next);
    const sync = () => {
      next.hidden = !link.getAttribute('href') || link.getAttribute('href') === '#' ||
        link.hidden || getComputedStyle(link).display === 'none';
    };
    new MutationObserver(sync).observe(link, {attributes:true, attributeFilter:['href','style','hidden','class']});
    sync();
  });
  document.querySelector('#tab-da > .card > p.steps')?.classList.add('clarity-superseded');

  // The extension is the primary route. All manual controls remain available
  // in their original DOM nodes, including the synced showcase mode selector.
  const steamLayout = document.querySelector('.steam-layout');
  const manual = steamLayout?.querySelector('.steam-col');
  const extension = steamLayout?.querySelector('.steam-extension-card');
  if (manual && extension) {
    const details = disclosure('manual', 'steamManualInstructions');
    steamLayout.append(details); details.append(manual);
    steamLayout.prepend(extension);
    steamLayout.classList.add('tool-steam-routes');
    const note = copyNode('p','mobile'); note.className = 'tool-mobile-note';
    extension.prepend(note);
  }

  function localize() {
    document.querySelectorAll('[data-clarity-copy]').forEach(node => {
      // Help buttons attached to the outcome must survive language switches.
      const value = t(node.dataset.clarityCopy);
      if (node.classList.contains('tool-outcome')) {
        if (node.firstChild?.nodeType === Node.TEXT_NODE) node.firstChild.nodeValue = value;
      } else node.textContent = value;
    });
  }
  window.addEventListener('sm:langchange', localize);
  localize();
})();
