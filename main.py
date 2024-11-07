import os
import wandb
import time
from utils.alert import send_discord_message
from dotenv import load_dotenv
import datetime as dt


load_dotenv()

PROJECT_NAME = 'sportstensor-vali-logs' # sportstensor wandb
ENTITY_NAME = 'sportstensor'

EXCLUDED_VALIDATORS = [
    'xjp',
]

wandb.login(key=os.getenv('WANDB_API_KEY'))

def get_wandb_runs(project, entity):
    """Fetch all active and past runs from the specified wandb project"""
    api = wandb.Api()
    runs = api.runs(f"{entity}/{project}")
    return runs

def check_stoppings(runs, webhook_url):
    """Check if any of the runs have crashed or failed"""
    stopped_runs = []
    stopped_at = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for run_lite in runs:
        run = wandb.Api().run(f"{ENTITY_NAME}/{PROJECT_NAME}/{run_lite['id']}")
        if run.state == 'finished':
            log_file = run.file('output.log').download(replace=True)

            with open(log_file.name, "r") as file:
                log_lines = file.readlines()
            
            # get the last 100 lines of logs and check for errors
            last_n_lines = log_lines[-100:]
            message = None
            for line in last_n_lines:
                if "KeyboardInterrupt" in line.lower() or "ctrl+c" in line.lower() or "keyboard interrupt" in line.lower():
                    message = f"Exception: KeyboardInterrupt"
                elif "exception" in line.lower() or "error" in line.lower():
                    message = line

            stopped_runs.append({
                'name': run.name,
                'id': run.id,
                'state': run.state,
                'url': run.url,
                'hotkey': run.config['hotkey'],
                'created_at': run.createdAt,
                'user': run.user.username,
            })

            if message:
                send_discord_message(webhook_url, f"Validator [`{run.user.username}`](<{run.url}>) {run.state} at `{stopped_at}`.\n```python\n{message}\n```")
            else:
                send_discord_message(webhook_url, f"Validator [`{run.user.username}`](<{run.url}>) {run.state} at `{stopped_at}`. No exceptions found in the logs.")
        elif run.state == 'crashed' or run.state == 'failed':
            stopped_runs.append({
                'name': run.name,
                'id': run.id,
                'state': run.state,
                'url': run.url,
                'hotkey': run.config['hotkey'],
                'created_at': run.createdAt,
                'user': run.user.username,
            })
            send_discord_message(webhook_url, f"Validator [`{run.user.username}`](<{run.url}>) {run.state} at `{stopped_at}`.")

    return stopped_runs

def check_running(runs, stopped_runs=[], webhook_url=None):
    """Check if any of the runs are still running"""
    running_runs = []
    stopped_users = []
    restarted_at = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if stopped_runs:
        stopped_users = [run['user'] for run in stopped_runs]
    for run in runs:
        # print(run.__dict__)
        if run.user.username in EXCLUDED_VALIDATORS:
            continue
        if run.state == 'running':
            running_runs.append({
                'name': run.name,
                'id': run.id,
                'state': run.state,
                'url': run.url,
                'hotkey': run.config['hotkey'],
                'created_at': run.createdAt,
                'user': run.user.username
            })
            if stopped_users and run.user.username in stopped_users:
                send_discord_message(webhook_url, f"Validator [`{run.user.username}`](<{run.url}>) restarted at `{restarted_at}`.")
    return running_runs

def sync_running_runs(project, entity, stopped_runs=[], webhook_url=None):
    """Sync the wandb runs with the local directory"""
    runs = get_wandb_runs(project, entity)
    running_runs = check_running(runs, stopped_runs, webhook_url)

    return running_runs


def monitor_wandb_logs(project, entity, webhook_url, interval=60):
    """
        Continuously monitor wandb logs, save the runs in a list and check for crashes.
        If any crashes are found, check the latest lines of logs and if there's exception, send a message to the sportstensor discord channel (#wandb-alerts).
    """
    running_runs = sync_running_runs(project, entity)
    print(f"{len(running_runs)} running validators found.")

    # send initial info about running validators
    # message = "**Running validators**\n"
    # for run in running_runs:
    #     message += f"- [{run['user']}: ({run['hotkey']})](<{run['url']}>)\n"
    # send_discord_message(webhook_url, message)

    print("Start monitoring validators on wandb...")
    while True:
        try:
            print("Checking for crashed validators...")
            stopped_runs = check_stoppings(running_runs, webhook_url)

            if stopped_runs:
                running_runs = sync_running_runs(project, entity, stopped_runs, webhook_url)

            print("Waiting for 60 seconds...")
            time.sleep(interval)

        except Exception as e:
            print(f"Error: {e}")
            continue


if __name__ == '__main__':
    webhook_url = os.getenv('DISCORD_WEBHOOK_URL')

    # start monitoring wandb logs
    monitor_wandb_logs(PROJECT_NAME, ENTITY_NAME, webhook_url, interval=60)