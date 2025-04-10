// Per-tool progress formatter dispatch

export function formatToolProgress(progress) {
  const formatter = toolFormatters[progress.tool] || defaultFormatter;
  return formatter(progress);
}

const toolFormatters = {
  view_file: formatViewFile,
  find_files: formatFindFiles,
  search_text: formatFindFiles,  // similar output
  bash_exec: formatBashExec,
  fetch_url: formatFetchUrl,
  create_file: formatCreateFile,
  create_directory: formatCreateDirectory,
  move_file: formatMoveFile,
  remove_file: formatRemoveFile,
  file_str_replace: formatFileStrReplace,
  ask_user: formatAskUser
};

function escape(s) {
  return (s || '').toString().replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function makeContentLink(content, lang = '') {
  const index = window.contentStore.push(content) - 1;
  const lineCount = content.split(/\r?\n/).length;
  return `<a href="#" onclick="showContentPopup(${index}, '${lang}'); return false;">${lineCount} line${lineCount !== 1 ? 's' : ''}</a>`;
}

function defaultFormatter(progress) {
  if(progress.event === 'start') {
    return `[${progress.tool}] starting`;
  } else if(progress.event === 'finish') {
    if(progress.error) {
      return `<span style='color:red'>Error:</span> ${escape(progress.error)}`;
    } else {
      return `[${progress.tool}] finished`;
    }
  } else {
    return `<pre>${escape(JSON.stringify(progress, null, 2))}</pre>`;
  }
}

function formatViewFile(progress) {
  const args = progress.args || {};
  const lang = (args.path||'').endsWith('.py') ? 'python' :
               (args.path||'').endsWith('.sh') ? 'bash' :
               (args.path||'').endsWith('.json') ? 'json' :
               (args.path||'').endsWith('.md') ? 'markdown' : '';

  if(progress.event === 'start') {
    return `Viewing ${args.path} lines ${args.start_line || 1} to ${args.end_line || 'end'}`;
  }
  if(progress.event === 'finish') {
    let content = '';
    if(typeof progress.result === 'string') {
      content = progress.result.split(/\r?\n/).map(line => line.replace(/^\s*\d+:\s*/, '')).join('\n');
    }
    const link = makeContentLink(content, lang);
    const count = content.trim() === '' ? 0 : content.split(/\r?\n/).length;
    return `${count} line${count !== 1 ? 's' : ''} (${link})`;
  }
  return '';
}

function formatFindFiles(progress) {
  const args = progress.args || {};
  if(progress.event === 'start') {
    return `Searching in ${args.directory}`;
  }
  if(progress.event === 'finish') {
    let content = '';
    let count = 0;
    if(Array.isArray(progress.result)) {
      content = progress.result.join('\n');
      count = progress.result.length;
    } else if(typeof progress.result === 'string') {
      content = progress.result;
      count = content.trim() === '' ? 0 : content.trim().split(/\r?\n/).length;
    }
    const link = makeContentLink(content);
    return `Found ${count} item${count !== 1 ? 's' : ''} (${link})`;
  }
  return '';
}

function formatBashExec(progress) {
  if(progress.event === 'start') return 'Running command';
  if(progress.event === 'finish') {
    const codeMatch = progress.result && progress.result.match(/returncode: ([-\d]+)/);
    const code = codeMatch ? codeMatch[1] : '?';
    return `Command finished (code ${code})`;
  }
  return '';
}

function formatFetchUrl(progress) {
  const args = progress.args || {};
  if(progress.event === 'start') return `Fetching ${args.url}`;
  if(progress.event === 'finish') return `Fetched ${args.url}`;
  return '';
}

function formatCreateFile(progress) {
  const args = progress.args || {};
  if(progress.event === 'start') return `Creating file ${args.path}`;
  if(progress.event === 'finish') return `Created file ${args.path}`;
  return '';
}

function formatCreateDirectory(progress) {
  const args = progress.args || {};
  if(progress.event === 'start') return `Creating directory ${args.path}`;
  if(progress.event === 'finish') return `Created directory ${args.path}`;
  return '';
}

function formatMoveFile(progress) {
  const args = progress.args || {};
  if(progress.event === 'start') return `Moving ${args.source_path} → ${args.destination_path}`;
  if(progress.event === 'finish') return `Moved ${args.source_path} → ${args.destination_path}`;
  return '';
}

function formatRemoveFile(progress) {
  const args = progress.args || {};
  if(progress.event === 'start') return `Removing ${args.path}`;
  if(progress.event === 'finish') return `Removed ${args.path}`;
  return '';
}

function formatFileStrReplace(progress) {
  const args = progress.args || {};
  if(progress.event === 'start') return `Replacing in ${args.path}`;
  if(progress.event === 'finish') return `Replaced in ${args.path}`;
  return '';
}

function formatAskUser(progress) {
  if(progress.event === 'start') return 'Waiting for user input';
  if(progress.event === 'finish') return 'User input done';
  return '';
}
