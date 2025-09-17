import boto3 
from botocore.config import Config
from botocore.exceptions import NoCredentialsError, ClientError,BotoCoreError





def user_is_authenticated(profile:str):
    try:
        session = boto3.Session(profile_name=profile)
        sts = session.client("sts")
        ident = sts.get_caller_identity()
        account_id = ident["Account"]
        return True
    except NoCredentialsError:
        print("No credentials — user probably never logged in.")
    except ClientError as e:
        if e.response["Error"]["Code"] in ("UnauthorizedSSOToken", "ExpiredToken", "InvalidClientTokenId"):
            print("Token expired — please run `aws sso login --profile clauth`.")
            return False
        else:
            raise

def list_bedrock_profiles(profile: str, region: str,provider='anthropic'):
    session = boto3.Session(profile_name=profile, region_name=region,)
    client = session.client("bedrock")

    try:
        resp = client.list_inference_profiles()
        model_arns= [p["inferenceProfileArn"] for p in resp.get("inferenceProfileSummaries", [])]
        model_arn_by_provider = [arn for arn in model_arns if provider in arn]
        model_ids = [p.split('/')[-1] for p in model_arn_by_provider]
        return model_ids,model_arn_by_provider
    except (BotoCoreError, ClientError) as e:
        print("Error listing inference profiles:", e)
        return [],[]
    
if __name__=='__main__':
    p=list_bedrock_profiles(profile='clauth',region='ap-southeast-2')
    print('===============')
    print(p)