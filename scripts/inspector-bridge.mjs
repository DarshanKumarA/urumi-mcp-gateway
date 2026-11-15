// Invoke the official Inspector CLI with credentials supplied only over stdin.
import { pathToFileURL } from 'node:url';

let input = '';
for await (const chunk of process.stdin) {
  input += chunk;
  if (input.length > 32768) throw new Error('INPUT_LIMIT');
}
const request = JSON.parse(input);
const { runCli } = await import(pathToFileURL(process.argv[2]).href);
const argv = ['node', 'inspector', request.url, '--transport', 'http',
  '--method', request.method, '--format', 'json', '--quiet', '--stored-auth-only'];
if (request.tool) argv.push('--tool-name', request.tool,
  '--tool-args-json', JSON.stringify(request.arguments));
argv.push('--header', 'Authorization: Bearer ' + request.key);
try {
  await runCli(argv);
} catch (error) {
  // Inspector errors may contain server output; keep only the classification.
  console.error(JSON.stringify({ error: 'INSPECTOR_FAILED', code: error.exitCode ?? null }));
  process.exitCode = 1;
}
