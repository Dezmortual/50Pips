"""Gunicorn config — makes the trading loop run in the worker that serves
the dashboard.

WHY THIS EXISTS: some gunicorn setups use --preload, which imports the app
in the MASTER process and forks workers from it. Any background thread
started at import time (our trading loop) keeps running in the master,
while the dashboard is served by a forked child holding only a frozen
snapshot of the bot's in-memory log and state. Result: dashboard never
updates, charts stay empty, and Start/Stop controls nothing.

Starting the loop in the post_fork hook guarantees it runs in the same
process that serves HTTP — no matter how gunicorn is invoked.
"""

# One worker = one trading loop. Multiple workers would each run their own
# loop and split-brain the bot state. Threads handle concurrent requests.
workers = 1
threads = 4
preload_app = False


def post_fork(server, worker):
    import bot
    bot.start_background()
    server.log.info("trading loop started in worker (pid %s)", worker.pid)
