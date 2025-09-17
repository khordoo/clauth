import typer
import click
import subprocess
import os
import boto3
import clauth.aws_utils as aws

app = typer.Typer()
env = os.environ.copy()
#TODO: get a list of availbale models from aws cli

default = {
    "profile": "clauth",
    'session_name':'clauth-session',
    "sso_start_url ": "https://d-97671967ae.awsapps.com/start/#",
    "sso_region": "ap-southeast-2",
    'output':'json',
    "model_ids": [None],
    "model_id_to_arn":{}
}


@app.command()
def init(
    profile: str = default["profile"],
    sso_region=default["sso_region"],
    sso_start_url=default["sso_start_url "],
    session_name= default['session_name']
):
    print("""
    Setting up aws profile. Select the AWS account to be used for Claude Code
    General Info: 
        SSO start URL : https://d-97671967ae.awsapps.com/start/#
        SSO Region: ap-southeast-2
          
          """)
    args = {
        "sso_start_url": sso_start_url,
        "sso_region": sso_region,
        "region": sso_region,
        'output': default['output'],
        'sso_session':'claude-auth',
        'sso_session.session_name.name': session_name #.name is dummy and can be anything just to force the creation of session name
    }
    try:
        # Setup the default profile entries for better UX
        for arg, value in args.items():
            # unsert to aovid duplicated
            subprocess.run(
                ["aws", "configure", "set", arg, value, "--profile", profile],
                check=True,
            )
        print('Succesfuly set the args')

        subprocess.run(["aws", "configure", "sso", "--profile", profile], check=True)
        subprocess.run(["aws", "sso", "login", "--profile", profile])
        print(f"Successfuly sso login using profile: {profile}")
        # model_ids, model_arns = aws.list_bedrock_profiles(profile=default["profile"],region=default['sso_region'])
        # default['model_ids']=model_ids
        # default['model_id_to_arn'] = {id:arn for id,arn in zip(model_ids,model_arns)}
        print('Avilbale anthroipci modesl:',  default['model_id_to_arn'])
        
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
def list_models(profile=default["profile"],region=default['sso_region']):
    if not aws.user_is_authenticated(profile=default["profile"]):
        exit('Crendetial is not set please run clauth init to loginto aws and authentcate')
    model_ids, model_arns = aws.list_bedrock_profiles(profile=default["profile"],region=default['sso_region'])
    for model_id in model_ids:
        print(model_id)


# @app.command()
# def demo(
#     profile: str = typer.Option(default["profile"], help="AWS profile"),
#     region: str = typer.Option(default["region"], help="AWS region"),
#     anthropic_model: str = typer.Option(
#         MODEL_IDS[0],
#         click.Choice(MODEL_IDS, case_sensitive=False),
#         help="Pick which Anthropic model to use",
#         show_choices=True,
#     ),
# ):
#     typer.echo(f"profile={profile}, region={region}, model={anthropic_model}")
def validate_model_id(id: str):
    model_ids, model_arns = aws.list_bedrock_profiles(profile=default["profile"],region=default['sso_region'])
    if id not in model_ids:
        raise typer.BadParameter(f'{id} is not valid or supported model is. Valid Models: {model_ids}')
    return id


@app.command()
def start(
    profile: str =  typer.Option(default["profile"], '--profile',help='AWS profile name with access to bedrock'),
    default_model_id =  typer.Option(..., '--model','-m', help='AWS bedrock model ID',callback=validate_model_id)
):
    
    #TODO: extract the apac part from the arn so we can specify a defualt model name like sunnet 4 and then 
    #we only attach the region to the first part ot make it work!
    if not aws.user_is_authenticated(profile=default["profile"]):
        exit('Crendetial is not set please run clauth init to loginto aws and authentcate')
    

  
    model_ids, model_arns = aws.list_bedrock_profiles(profile=default["profile"],region=default['sso_region'])
    model_map = {id:arn for id,arn in zip(model_ids,model_arns)}
    if default_model_id not in model_ids:
        exit(f'The provided model id: {default_model_id} is not valid or supported. To view a list of availbalw modes run : clauth list-models')
    
    # aws_account = get_aws_account()
    # model_arn = f"arn:aws:bedrock:{default['sso_region']}:{aws_account}:inference-profile/{default_model_id}"
    print("model arn:", model_map[default_model_id])
    env.update(
        {
            "AWS_PROFILE": profile,
            "AWS_REGION": default["sso_region"],
            "CLAUDE_CODE_USE_BEDROCK": "1",
            "ANTHROPIC_MODEL": model_map[default_model_id],
            "ANTHROPIC_SMALL_FAST_MODEL_AWS_REGION": model_map[default_model_id],
        }
    )

    claude_path = get_claude_path()
    subprocess.run([claude_path], env=env, check=True)


if __name__ == "__main__":
    app()
