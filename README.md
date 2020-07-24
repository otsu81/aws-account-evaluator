# AWS Stale Account Detection

Deploys a Lambda function using AWS SAM, intended to analyze all accounts in an AWS Organization. Tries to deduce when the last time the account was utilized and what the spending trend of the account in question.

Parameters are set in the Cloudformation template or by creating a parameters file. For Axis internal use, defaults can be used.

## Requirements
The lambda function needs to have permissions to assume role in the Organization, and every child account. Example policy:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "sts:AssumeRole",
            "Resource": "*"
        }
    ]
}
```

## Usage

### Local with SAM
```bash
sam local invoke -e events/[eventfile].json
```

### Remote, with AWS CLI
With AWS CLI, function name is decided by `template.yaml` and service parameter, output to file `response.json`:

```bash
aws lambda invoke --function-name [YOUR-FUNCTION-NAME] --payload file://event.json response.json
```

## Deployment

## TODO