import typer
import subprocess
import os
import clauth.aws_utils as aws
from InquirerPy import inquirer
from textwrap import dedent
from rich.console import Console
from InquirerPy import get_style



app = typer.Typer()
env = os.environ.copy()
console = Console()
#TODO: get a list of availbale models from aws cli

default = {
    "profile": "clauth",
    'cli_name':'claude',
    'session_name':'clauth-session',
    "sso_start_url": "https://d-97671967ae.awsapps.com/start/#",
    "sso_region": "ap-southeast-2",
    'output':'json',
    'supported_model_providers':[["Anthropic"]],
    "model_ids": [None],
    "model_id_to_arn":{}
}

custom_style = get_style({
    "questionmark": "bold",
    "instruction": "dim",
    "answer": "bold",
    "pointer": "ansiblue",        # was bold cyan
    "highlighted": "ansiblue",    # current row color
    "selected": "ansiblue"
})


@app.command(
        help=(
        "First-time setup for CLAUTH: creates an SSO session, links an AWS profile, "
        "runs the AWS SSO wizard, logs you in, and optionally launches the Claude CLI."
    )
)
def init(
  profile: str = typer.Option(
        default["profile"],
        "--profile",
        "-p",
        help="AWS profile to create or update (saved under [profile <name>] in ~/.aws/config).",
        show_default=True,
        rich_help_panel="AWS Profile",
    ),
    session_name: str = typer.Option(
        default["session_name"],
        "--session-name",
        "-s",
        help="Name of the SSO session to create (saved under [sso-session <name>] in ~/.aws/config).",
        show_default=True,
        rich_help_panel="AWS SSO",
    ),
    sso_start_url: str = typer.Option(
        default["sso_start_url"],
        "--sso-start-url",
        help="IAM Identity Center (SSO) Start URL (e.g., https://d-…awsapps.com/start/).",
        show_default=True,
        rich_help_panel="AWS SSO",
    ),
    sso_region: str = typer.Option(
        default["sso_region"],
        "--sso-region",
        help="Region that hosts your IAM Identity Center (SSO) instance.",
        show_default=True,
        rich_help_panel="AWS SSO",
    ),
    region: str = typer.Option(
        default["sso_region"],
        "--region",
        "-r",
        help="Default AWS client region for this profile (used for STS/Bedrock calls).",
        show_default=True,
        rich_help_panel="AWS Profile",
    ),
    auto_start: bool = typer.Option(
        True,
        "--auto-start/--no-auto-start",
        help="Launch the Claude CLI immediately after successful setup.",
        rich_help_panel="Behavior",
    ),
  ):
    show_welcome_logo(console=console)
   
    args = {
        "sso_start_url": sso_start_url,
        "sso_region": sso_region,
        "region": sso_region,
        'output': default['output'],
        'sso_session':'claude-auth',
        'sso_session.session_name.name': session_name #.name is dummy and can be anything just to force the creation of session name
    }
    try:
        typer.secho("Step 1/3 — Configuring AWS SSO profile...",fg=typer.colors.BLUE)
        # Setup the default profile entries for better UX
        for arg, value in args.items():
            # unsert to aovid duplicated
            subprocess.run(
                ["aws", "configure", "set", arg, value, "--profile", profile],
                check=True,
            )
       
        typer.echo("Opening the AWS SSO wizard. You can accept the defaults unless your team specifies otherwise.")


        subprocess.run(["aws", "configure", "sso", "--profile", profile], check=True)
        subprocess.run(["aws", "sso", "login", "--profile", profile])
        typer.secho(f"SSO login successful for profile '{profile}'.", fg=typer.colors.GREEN)


        typer.secho("Step 2/3 — Discovering available inference profiles (models)...", fg=typer.colors.BLUE)

        #TODO: add cloud provider later mayber google GCP as well
        # provider = inquirer.select(
        # message="Choose provider",
        # choices=["Anthropic", "Amazon", "Mistral"],

        # pointer="❯",
        # # style=style,
    # ).execute()
        model_ids, model_arns = aws.list_bedrock_profiles(profile=default["profile"],region=region)
        model_id_default = inquirer.select(
            message="Select your [default] model:",
            instruction="↑↓ move • Enter select",
            pointer="❯",                  # nice pointer glyph
            amark="✔",   
            choices=model_ids,
            default=model_ids[0],
                 # selected marker
            style=custom_style,
            max_height="100%"
        ).execute()
        model_id_fast = inquirer.select(
            message="Select your [small/fast] model (you can choose the same as default):",
            instruction="↑↓ move • Enter select",
            pointer="❯",                  # nice pointer glyph
            amark="✔",   
            choices=model_ids,
            default=model_ids[-1],
            style=custom_style,
            max_height="100%"
        ).execute()
        typer.echo(f"Default model: {model_id_default}")
        typer.echo(f"Small/Fast model: {model_id_fast}")
        model_map = {id:arn for id,arn in zip(model_ids,model_arns)}
        env.update(
            {
                "AWS_PROFILE": profile,
                "AWS_REGION": default["sso_region"],
                "CLAUDE_CODE_USE_BEDROCK": "1",
                "ANTHROPIC_MODEL": model_map[model_id_default],
                "ANTHROPIC_SMALL_FAST_MODEL_AWS_REGION": model_map[model_id_fast],
            }
        )
        typer.echo(f"""default model: {model_id_default}\n small/fast model: {model_id_fast}\n""")
        if auto_start:
            typer.secho("Setup complete ✅", fg=typer.colors.GREEN)
            typer.secho("Step 3/3 — Launching Claude Code...",fg=typer.colors.BLUE)
            claude_path = get_app_path(default['cli_name'])
            clear_screen()
            subprocess.run([claude_path], env=env, check=True)
        else:
            typer.echo("Step 3/3 — Setup complete.", fg=typer.colors.GREEN)
            typer.echo("Run the Claude Code CLI when you’re ready:  [bold]claude[/bold]")

      

    except subprocess.CalledProcessError as e:
        typer.secho(f"Setup failed. Exit code: {e.returncode}", fg=typer.colors.RED)
        exit(f"Failed to setup. Error Code: {e.returncode}")
   
def show_welcome_logo(console: Console)->None:
    logo = """┌─────────────── CLAUTH ───────────────┐
│  Claude + AWS SSO helper for Bedrock │
└──────────────────────────────────────┘"""
    console.print(logo, style="bold cyan")
   
    console.print(dedent("""
        [bold]Welcome to CLAUTH[/bold]
        Let’s set up your environment for Claude Code on Amazon Bedrock.

        Prerequisites:
          • AWS CLI v2
          • Claude Code CLI

        Tip: run [bold]clauth init --help[/bold] to view options.
    """).strip())


def clear_screen():
    os.system('cls' if os.name=='nt' else 'clear')


def get_app_path(exe_name:str='claude'):
    try:
        result = subprocess.run(
            ["where", exe_name], capture_output=True, text=True, check=True
        )
        claude_path = result.stdout.splitlines()[1]  # TODO: we sleected .cmd
        return claude_path
    except subprocess.CalledProcessError as e:
         exit(f'Setup Fialed. {exe_name} not found on the system.')



@app.command()
def list_models(profile=default["profile"],region=default['sso_region'], show_arn=False):
    if not aws.user_is_authenticated(profile=profile):
        exit("Credentials are missing or expired. Run `clauth init` to authenticate with AWS.")

    model_ids, model_arns = aws.list_bedrock_profiles(profile=profile,region=region)
    for model_id, model_arn in zip(model_ids,model_arns):
        if show_arn:
            print(model_id , ' --> ', model_arn)
        else:
            print(model_id)




def validate_model_id(id: str):
    model_ids, model_arns = aws.list_bedrock_profiles(profile=default["profile"],region=default['sso_region'])
    if id not in model_ids:
        raise typer.BadParameter(f'{id} is not valid or supported model is. Valid Models: {model_ids}')
    return id


# @app.command()
# def start(
#     profile: str =  typer.Option(default["profile"], '--profile',help='AWS profile name with access to bedrock'),
# ):
    
#     #TODO: extract the apac part from the arn so we can specify a defualt model name like sunnet 4 and then 
#     #we only attach the region to the first part ot make it work!
#     if not aws.user_is_authenticated(profile=default["profile"]):
#         exit('Crendetial is not set please run clauth init to loginto aws and authentcate')
    

  
#     model_ids, model_arns = aws.list_bedrock_profiles(profile=default["profile"],region=default['sso_region'])
#     model_id_default = inquirer.fuzzy(
#         message="Select defalt model:'",
#         choices=model_ids,
#         # default="he",
#         max_height="70%"
#     ).execute()
#     model_id_fast = inquirer.fuzzy(
#         message="Select defalt model:'",
#         choices=model_ids,
#         default=model_id_default,
#         max_height="70%"
#     ).execute()
#     model_map = {id:arn for id,arn in zip(model_ids,model_arns)}
#     print('default and fast:',model_id_default,model_id_fast)
#     env.update(
#         {
#             "AWS_PROFILE": profile,
#             "AWS_REGION": default["sso_region"],
#             "CLAUDE_CODE_USE_BEDROCK": "1",
#             "ANTHROPIC_MODEL": model_map[model_id_default],
#             "ANTHROPIC_SMALL_FAST_MODEL_AWS_REGION": model_map[model_id_fast],
#         }
#     )

    
#     claude_path = get_app_path()
#     subprocess.run([claude_path], env=env, check=True)


if __name__ == "__main__":

    app()
