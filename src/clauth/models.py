from clauth import aws_utils as aws
def model_picker(profile:str, region:str, provider:str='anthropic'):
    model_ids, model_arns = aws.list_bedrock_profiles(profile=profile,region=region)
    mapping ={}
    for model_id ,model_arn in zip(model_ids,model_arns):
        if provider not in model_id:
            continue
        mapping[model_id] = model_arn
    
    valid_model_ids = mapping.keys()
    
        

