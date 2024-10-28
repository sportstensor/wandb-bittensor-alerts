# wandb-bittensor-alerts

## Overview
`wandb-bittensor-alerts` is a tool designed to monitor Weights & Biases (wandb) logs and send alerts to a specified Discord channel. It helps track potential errors and exceptions in validator operations by providing real-time notifications.

## Features
- **Real-time Monitoring**: Continuously monitors wandb logs of validators, checking if a run has crashed, failed, or finished, and reads the logs.
- **Discord Integration**: Sends alerts directly to a designated Discord channel.

## Installation
To install the necessary dependencies, run:
```bash
pip install -r requirements.txt
```

## Usage
1. **Run**: Start the monitoring script:
    ```bash
    python main.py
    ```

## Configuration
Copy the `.env.sample` file to `.env` and store the `webhook_url` there.
```yaml
api_key=YOUR_WANDB_API_KEY 
webhook_url=YOUR_DISCORD_WEBHOOK_URL
```

## Contributing
Contributions are welcome! Please open an issue or submit a pull request.

## TODO
- Check logs for failed/crashed runs

## License
This project is licensed under the MIT License.
