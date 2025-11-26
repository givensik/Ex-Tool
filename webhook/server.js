const { createServer } = require('http');
const { parse } = require('url');
const next = require('next');
const { spawn } = require('child_process');
const cloudflaredPath = require('cloudflared').bin;

const dev = process.env.NODE_ENV !== 'production';
const hostname = 'localhost';
const port = parseInt(process.env.PORT || '3000', 10);
// when using middleware `hostname` and `port` must be provided below
const app = next({ dev, hostname, port });
const handle = app.getRequestHandler();

app.prepare().then(() => {
    createServer(async (req, res) => {
        try {
            // Be sure to pass `true` as the second argument to `url.parse`.
            // This tells it to parse the query portion of the URL.
            const parsedUrl = parse(req.url, true);
            const { pathname, query } = parsedUrl;

            if (pathname === '/a') {
                await app.render(req, res, '/a', query);
            } else if (pathname === '/b') {
                await app.render(req, res, '/b', query);
            } else {
                await handle(req, res, parsedUrl);
            }
        } catch (err) {
            console.error('Error occurred handling', req.url, err);
            res.statusCode = 500;
            res.end('internal server error');
        }
    })
        .once('error', (err) => {
            console.error(err);
            process.exit(1);
        })
        .listen(port, async () => {
            console.log(`> Ready on http://${hostname}:${port}`);

            console.log('---------------------------------------------------');
            console.log('> 🚀 Starting Cloudflare Tunnel...');

            // Start cloudflared tunnel
            const tunnel = spawn(cloudflaredPath, ['tunnel', '--url', `http://localhost:${port}`]);

            tunnel.stdout.on('data', (data) => {
                // cloudflared usually outputs to stderr, but we check stdout too
                const output = data.toString();
                // console.log(output); 
            });

            tunnel.stderr.on('data', (data) => {
                const output = data.toString();
                // Regex to find the trycloudflare.com URL
                const match = output.match(/https:\/\/[a-zA-Z0-9-]+\.trycloudflare\.com/);
                if (match) {
                    console.log(`> 🌐 Public URL: ${match[0]}`);
                    console.log('---------------------------------------------------');
                }
            });

            tunnel.on('close', (code) => {
                if (code !== 0) {
                    console.log(`Cloudflare tunnel process exited with code ${code}`);
                }
            });
        });
});