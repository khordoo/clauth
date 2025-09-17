import boto3 
from botocore.config import Config
from botocore.exceptions import NoCredentialsError, ClientError,BotoCoreError ,TokenRetrievalError





def user_is_authenticated(profile:str):
    try:
        session = boto3.Session(profile_name=profile)
        sts = session.client("sts")
        ident = sts.get_caller_identity()
        account_id = ident["Account"]
        print('User account:',account_id)
        return True
    except Exception as e:
        return False
    except NoCredentialsError or TokenRetrievalError:
        print("No credentials — user probably never logged in.")
        return False
    except ClientError as e:
        if e.response["Error"]["Code"] in ("UnauthorizedSSOToken", "ExpiredToken", "InvalidClientTokenId"):
            print("Token expired — please run `aws sso login --profile clauth`.")
            return False
        else:
            print('Error in getting the token')
            return False

def list_bedrock_profiles(profile: str, region: str,provider='anthropic', sort:bool=True):
    session = boto3.Session(profile_name=profile, region_name=region,)
    client = session.client("bedrock")
    #TODO: handle case when no model is avovable
    try:
        resp = client.list_inference_profiles()
        model_arns= [p["inferenceProfileArn"] for p in resp.get("inferenceProfileSummaries", [])]
        if model_arns and sort:
            model_arns.sort(reverse=True)
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