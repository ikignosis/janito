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
  const link = `<a href="#" onclick="showContentPopup(${index}, '${lang}'); return false;">${lineCount} line${lineCount !== 1 ? 's' : ''}</a>`;

  switch(progress.tool) {
    case 'view_file':
      breadcrumb = `Viewing ${link}`;
      break;
    case 'create_file':
      breadcrumb = `Finished creating file &gt; ${args.path}`; break;
    case 'create_directory':
      breadcrumb = `Finished creating directory &gt; ${args.path}`; break;
    case 'move_file':
      breadcrumb = `Finished moving &gt; ${args.source_path} &rarr; ${args.destination_path}`; break;
    case 'remove_file':
      breadcrumb = `Finished removing &gt; ${args.path}`; break;
    case 'file_str_replace':
      breadcrumb = `Finished replacing in &gt; ${args.path}`; break;
    case 'find_files':
      breadcrumb = `Finished searching in &gt; ${args.directory}`; break;
    case 'search_text':
      breadcrumb = `Finished searching text in &gt; ${args.directory}`; break;
    case 'bash_exec':
      breadcrumb = `Finished running command`; break;
    case 'fetch_url':
      breadcrumb = `Finished fetching URL &gt; ${args.url}`; break;
    case 'ask_user':
      breadcrumb = `User input finished`; break;
    default:
      breadcrumb = `[${progress.tool}] finished &gt; ` + Object.entries(args).map(([k,v])=>`${k}: ${v}`).join(', ');
  }

  return breadcrumb;
}
