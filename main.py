import os
import wandb
import time
from utils.alert import send_discord_message
from dotenv import load_dotenv
import datetime as dt


load_dotenv()

PROJECT_NAME = 'sportstensor-vali-logs' # sportstensor wandb
ENTITY_NAME = 'sportstensor'

wandb.login(key=os.getenv('WANDB_API_KEY'))

def get_wandb_runs(project, entity):
    """Fetch all active and past runs from the specified wandb project"""
    api = wandb.Api()
    runs = api.runs(f"{entity}/{project}")
    return runs

def check_crashes(runs, webhook_url):
    """Check if any of the runs have crashed or failed"""
    is_stopped = False
    stopped_at = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for run_lite in runs:
        run = wandb.Api().run(f"{ENTITY_NAME}/{PROJECT_NAME}/{run_lite['id']}")
        if run.state == 'finished':
            is_stopped = True
            log_file = run.file('output.log').download(replace=True)

            with open(log_file.name, "r") as file:
                log_lines = file.readlines()
            
            # get the last 100 lines of logs and check for errors
            last_n_lines = log_lines[-100:]
            message = None
            for line in last_n_lines:
                if "KeyboardInterrupt" in line.lower():
                    message = f"Exception: KeyboardInterrupt"
                elif "exception" in line.lower() or "error" in line.lower():
                    message = line

            if message:
                send_discord_message(webhook_url, f"Validator `{run.user}` {run.state} at {stopped_at}.\n```python\n{message}\n```")
            else:
                print("No errors found.")
        elif run.state == 'crashed' or run.state == 'failed':
            is_stopped = True
            send_discord_message(webhook_url, f"Validator `{run.user}` {run.state} at {stopped_at}.")

    return is_stopped

def check_running(runs):
    """Check if any of the runs are still running"""
    running_runs = []
    for run in runs:
        # print(run.__dict__)
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
    return running_runs

def sync_running_runs(project, entity):
    """Sync the wandb runs with the local directory"""
    runs = get_wandb_runs(project, entity)
    running_runs = check_running(runs)

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
            is_stopped = check_crashes(running_runs, webhook_url)

            if is_stopped:
                running_runs = sync_running_runs(project, entity)

            print("Waiting for 60 seconds...")
            time.sleep(interval)

        except Exception as e:
            print(f"Error: {e}")
            continue


if __name__ == '__main__':
    webhook_url = os.getenv('DISCORD_WEBHOOK_URL')

    # start monitoring wandb logs
    monitor_wandb_logs(PROJECT_NAME, ENTITY_NAME, webhook_url, interval=60)