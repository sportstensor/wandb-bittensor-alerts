import os
import wandb
import time
from utils.alert import send_discord_message
from dotenv import load_dotenv


load_dotenv()

PROJECT_NAME = 'sportstensor-vali-logs' # sportstensor wandb
ENTITY_NAME = 'sportstensor'

wandb.login(key=os.getenv('WANDB_API_KEY'))

def get_wandb_runs(project, entity):
    """Fetch all active and past runs from the specified wandb project"""
    api = wandb.Api()
    runs = api.runs(f"{entity}/{project}")
    return runs

def check_crashes(runs):
    """Check if any of the runs have crashed or failed"""
    crashed_runs = []
    for run_lite in runs:
        run = wandb.Api().run(f"{ENTITY_NAME}/{PROJECT_NAME}/{run_lite['id']}")
        if run.state == 'failed' or run.state == 'crashed' or run.state == 'finished':
            send_discord_message(webhook_url, f"Validator {run.user.username}({run.config['hotkey']}) stopped with state: {run.state}. Check the logs [here](<{run.url}>).")
            crashed_runs.append({
                'name': run.name,
                'id': run.id,
                'state': run.state,
                'url': run.url,
                'hotkey': run.config['hotkey'],
                'created_at': run.createdAt,
                'user': run.user.username
            })
    return crashed_runs

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

def monitor_wandb_logs(project, entity, webhook_url, interval=60):
    """
        Continuously monitor wandb logs, save the runs in a list and check for crashes.
        If any crashes are found, check the latest lines of logs and if there's exception, send a message to the sportstensor discord channel (#wandb-alerts).
    """
    runs = get_wandb_runs(project, entity)
    running_runs = check_running(runs)
    print(f"{len(running_runs)} running validators found.")

    # send initial info about running validators
    message = "**Running validators**\n"
    for run in running_runs:
        message += f"- [{run['user']}: ({run['hotkey']})](<{run['url']}>)\n"
    send_discord_message(webhook_url, message)

    print("Start monitoring validators on wandb...")
    while True:
        try:
            print("Checking for crashed validators...")
            crashed_runs = check_crashes(running_runs)
            if len(crashed_runs) == 0:
                print("No crashed validators found.")
            else:
                for run in crashed_runs:
                    if run['state'] == 'finished':
                        run_log = wandb.Api().run(f"{entity}/{project}/{run['id']}")
                        log_file = run_log.file('output.log').download(replace=True)

                        with open(log_file.name, "r") as file:
                            log_lines = file.readlines()
                        
                        # get the last 100 lines of logs and check for errors
                        last_n_lines = log_lines[-100:]
                        has_error = any("error" in line.lower() for line in last_n_lines)
                        has_exception = any("exception" in line.lower() for line in last_n_lines)

                        print("Last N lines of logs:")
                        print("".join(last_n_lines))

                        if has_error:
                            print("Error found in the logs!")
                            send_discord_message(webhook_url, f"Error found in the logs of {run['user']}({run['hotkey']}).")
                        elif has_exception:
                            print("Exception found in the logs!")
                            send_discord_message(webhook_url, f"Exception found in the logs of {run['user']}({run['hotkey']}).")
                        else:
                            print("No errors found.")
                    runs = get_wandb_runs(project, entity)
                    running_runs = check_running(runs)

            print("Waiting for 60 seconds...")
            time.sleep(interval)
            
        except Exception as e:
            print(f"Error: {e}")
            continue


if __name__ == '__main__':
    webhook_url = os.getenv('DISCORD_WEBHOOK_URL')

    # start monitoring wandb logs
    monitor_wandb_logs(PROJECT_NAME, ENTITY_NAME, webhook_url, interval=60)