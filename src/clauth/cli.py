import typer
import subprocess
import os

app = typer.Typer()
env = os.environ.copy()
#TODO: get a list of availbale models from aws cli
default = {
    "profile": "clauth",
    "sso_start_url ": "https://d-97671967ae.awsapps.com/start/#",
    "region": "ap-southeast-2",
    "anthropic_model": [
        "apac.anthropic.claude-sonnet-4-20250514-v1:0",
        "apac.anthropic.claude-3-7-sonnet-20250219-v1:0",
    ],
}


@app.command()
def init(
    profile: str = default["profile"],
    region=default["region"],
    sso_start_url=default["sso_start_url "],
):
    print("""
    Setting up aws profile. Select the AWS account to be used for Claude Code
    General Info: 
        SSO start URL : https://d-97671967ae.awsapps.com/start/#
        SSO Region: ap-southeast-2
          
          """)
    args = {
        "sso_start_url": sso_start_url,
        "sso_region": region,
        "region": region,
    }
    try:
        # Setup the default profile entries for better UX
        for arg, value in args.items():
            # unsert to aovid duplicated
            subprocess.run(
                ["aws", "configure", "set", arg, value, "--profile", profile],
                check=True,
            )

        subprocess.run(["aws", "configure", "sso", "--profile", profile], check=True)
        subprocess.run(["aws", "sso", "login", "--profile", profile])
        print(f"Successfuly sso login using profile: {profile}")
    except subprocess.CalledProcessError as e:
        exit(f"Command failed with code {e.returncode}")
    print("Successfuyl set the profile")


def get_claude_path():
    result = subprocess.run(
        ["where", "claude"], capture_output=True, text=True, check=True
    )
    claude_path = result.stdout.splitlines()[1]  #
    print("Claude path is:", claude_path)
    return claude_path


def get_aws_account():
    try:
        result = subprocess.run(
            [
                "aws",
                "sts",
                "get-caller-identity",
                "--profile",
                default["profile"],
                "--query",
                "Account",
                "--output",
                "text",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        account_id = result.stdout.strip()
        print("Aws Accoutn ID:", account_id)
        return account_id
    except subprocess.CalledProcessError as e:
        exit(f"Command failed with code {e}")




@app.command()
def start(
    profile: str = default["profile"],
    anthropic_model: str = typer.Option(
        default["anthropic_model"][0],
        case_sensitive=False,
        help="Pick which Anthropic model to use",
        show_choices=True,
    ),
):
    aws_account = get_aws_account()
    model_arn = f"arn:aws:bedrock:{default['region']}:{aws_account}:inference-profile/{anthropic_model}"
    print("model arn:", model_arn)
    env.update(
        {
            "AWS_PROFILE": profile,
            "AWS_REGION": default["region"],
            "CLAUDE_CODE_USE_BEDROCK": "1",
            "ANTHROPIC_MODEL": model_arn,
            "ANTHROPIC_SMALL_FAST_MODEL_AWS_REGION": model_arn,
        }
    )

    claude_path = get_claude_path()
    subprocess.run([claude_path], env=env, check=True)


if __name__ == "__main__":
    app()
