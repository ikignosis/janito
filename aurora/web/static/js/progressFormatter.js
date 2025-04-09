// progressFormatter.js

export function formatProgress(progress, args) {
  let breadcrumb = '';
  let lineCount = 0;
  let content = '';

  if (progress.result && typeof progress.result === 'string') {
    content = progress.result;
    lineCount = content.split(/\r?\n/).length;
  }

  const safeContent = content.replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const escapedContent = safeContent.replace(/\\/g, '\\\\').replace(/`/g, '\\`').replace(/\$\{/g, '\\${}');

  let lang = '';
  if(args.path) {
    if(args.path.endsWith('.py')) lang = 'python';
    else if(args.path.endsWith('.sh') || args.path.endsWith('.bash')) lang = 'bash';
    else if(args.path.endsWith('.json')) lang = 'json';
    else if(args.path.endsWith('.md') || args.path.endsWith('.markdown')) lang = 'markdown';
  }

  const index = window.contentStore.push(content) - 1;
  const link = `<a href=\"#\" onclick=\"showContentPopup(${index}, '${lang}'); return false;\">${lineCount} line${lineCount !== 1 ? 's' : ''}</a>`;

  const isStart = progress.event === 'start';

  if(isStart) {
    switch(progress.tool) {
      case 'view_file':
        breadcrumb = `Viewing ${args.path} lines ${args.start_line || 1} to ${args.end_line || 'end'}`;
        break;
      case 'create_file': {
        const newLines = args.content ? (args.content.match(/\n/g) || []).length + 1 : 0;
        const overwriteText = args.overwrite ? ' (overwriting)' : '';
        breadcrumb = `Creating file${overwriteText} ${args.path} (${newLines} lines)`;
        break;
      }
      case 'move_file':
        breadcrumb = `Moving ${args.source_path} → ${args.destination_path}`;
        break;
      case 'bash_exec':
        breadcrumb = `Running command: ${args.command}`;
        break;
      case 'create_directory':
        breadcrumb = `Creating dir ${args.path}`;
        break;
      case 'remove_file':
        breadcrumb = `Removing ${args.path}`;
        break;
      case 'file_str_replace':
        breadcrumb = `Replacing in ${args.path}`;
        break;
      case 'find_files':
        breadcrumb = `Searching in ${args.directory}`;
if(args.file_pattern || args.text_pattern || args.case_sensitive !== undefined) {
  const parts = [];
  if(args.file_pattern) parts.push(`file: ${args.file_pattern}`);
  if(args.text_pattern) parts.push(`text: ${args.text_pattern}`);
  if(args.case_sensitive !== undefined) parts.push(`case: ${args.case_sensitive}`);
  if(parts.length) breadcrumb += ' (' + parts.join(', ') + ')';
}
        break;
      case 'search_text':
        breadcrumb = `Searching text in ${args.directory}`;
if(args.file_pattern || args.text_pattern || args.case_sensitive !== undefined) {
  const parts = [];
  if(args.file_pattern) parts.push(`file: ${args.file_pattern}`);
  if(args.text_pattern) parts.push(`text: ${args.text_pattern}`);
  if(args.case_sensitive !== undefined) parts.push(`case: ${args.case_sensitive}`);
  if(parts.length) breadcrumb += ' (' + parts.join(', ') + ')';
}
        break;
      case 'fetch_url':
        breadcrumb = `Fetching ${args.url}`;
        break;
      case 'ask_user':
        breadcrumb = `Waiting user input`;
        break;
      default:
        breadcrumb = `[${progress.tool}] starting > ` + Object.entries(args).map(([k,v])=>`${k}: ${v}`).join(', ');
    }
  } else {
    switch(progress.tool) {
      case 'view_file':
        breadcrumb = `${link}`;
        break;
      case 'create_file': {
        const success = progress.result && progress.result.includes('Successfully');
        const overwriteText = args.overwrite ? ' (overwriting)' : '';
        breadcrumb = `${success ? 'Created' : 'Failed'}${overwriteText} ${args.path}`;
        break;
      }
      case 'create_directory':
        breadcrumb = `Created dir ${args.path}`; break;
      case 'move_file': {
        const success = progress.result && progress.result.includes('Successfully');
        breadcrumb = `${success ? 'Moved' : 'Failed move'} ${args.source_path} → ${args.destination_path}`;
        break;
      }
      case 'remove_file':
        breadcrumb = `Removed ${args.path}`; break;
      case 'file_str_replace':
        breadcrumb = `Replaced in ${args.path}`; break;
      case 'find_files':
        breadcrumb = `Searched in ${args.directory}`; break;
      case 'search_text':
        breadcrumb = `Searched text in ${args.directory}`; break;
      case 'bash_exec': {
        const codeMatch = progress.result && progress.result.match(/returncode: ([-\d]+)/);
        const code = codeMatch ? codeMatch[1] : '?';
        breadcrumb = `Command done (code ${code})`;
        break;
      }
      case 'fetch_url':
        breadcrumb = `Fetched ${args.url}`; break;
      case 'ask_user':
        breadcrumb = `User input done`; break;
      default:
        breadcrumb = `[${progress.tool}] done > ` + Object.entries(args).map(([k,v])=>`${k}: ${v}`).join(', ');
    }
  }

  return breadcrumb;
}
