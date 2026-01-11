from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_dynamodb as dynamodb,
    aws_lambda as _lambda,
    aws_events as events,
    aws_events_targets as targets,
    aws_lambda_event_sources as lambda_sources,
    CfnOutput,
)
from constructs import Construct
import os

class CdkAppStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1. DynamoDB Table
        table = dynamodb.Table(
            self, "JobsTable",
            partition_key=dynamodb.Attribute(
                name="job_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
            removal_policy=RemovalPolicy.DESTROY, # For dev/portfolio capability to clean up
        )

        # 2. Lambda Functions (Docker Image)
        # We use DockerImageCode.from_image_asset to specify the directory and the CMD override for each function.

        # Collector Lambda
        collector_fn = _lambda.DockerImageFunction(
            self, "CollectorFunction",
            code=_lambda.DockerImageCode.from_image_asset(
                directory="../app",
                cmd=["collector.handler"]
            ),
            architecture=_lambda.Architecture.X86_64,
            timeout=Duration.seconds(60),
            environment={
                "TABLE_NAME": table.table_name
            }
        )
        table.grant_write_data(collector_fn)

        # Matcher Lambda
        matcher_fn = _lambda.DockerImageFunction(
            self, "MatcherFunction",
            code=_lambda.DockerImageCode.from_image_asset(
                directory="../app",
                cmd=["matcher.handler"]
            ),
            architecture=_lambda.Architecture.X86_64,
            timeout=Duration.seconds(60),
            environment={
                "TABLE_NAME": table.table_name
            }
        )
        table.grant_read_write_data(matcher_fn)

        # Notifier Lambda
        notifier_fn = _lambda.DockerImageFunction(
            self, "NotifierFunction",
            code=_lambda.DockerImageCode.from_image_asset(
                directory="../app",
                cmd=["notifier.handler"]
            ),
            architecture=_lambda.Architecture.X86_64,
            timeout=Duration.seconds(60),
            environment={
                "TABLE_NAME": table.table_name
            }
        )
        table.grant_read_write_data(notifier_fn)

        # 4. Viewer Function (Web Dashboard)
        viewer_fn = _lambda.DockerImageFunction(
            self, "ViewerFunction",
            code=_lambda.DockerImageCode.from_image_asset(
                directory="../app",
                cmd=["viewer.handler"]
            ),
            architecture=_lambda.Architecture.X86_64,
            timeout=Duration.seconds(30),
            environment={
                "TABLE_NAME": table.table_name
            }
        )
        
        # Enable Function URL (Public)
        viewer_url = viewer_fn.add_function_url(
            auth_type=_lambda.FunctionUrlAuthType.NONE
        )
        
        # Permissions
        table.grant_read_data(viewer_fn) # Viewer only needs read access
        
        # Outputs
        CfnOutput(self, "ViewerUrl", value=viewer_url.url)

        # 3. Triggers

        # EventBridge Cron for Collector (Run every day at 10:00 AM UTC)
        rule = events.Rule(
            self, "DailyCollectionRule",
            schedule=events.Schedule.cron(minute="0", hour="10")
        )
        rule.add_target(targets.LambdaFunction(collector_fn))

        # DynamoDB Stream for Matcher (Trigger on INSERT)
        matcher_fn.add_event_source(lambda_sources.DynamoEventSource(
            table,
            starting_position=_lambda.StartingPosition.TRIM_HORIZON,
            batch_size=1,
            filters=[
                _lambda.FilterCriteria.filter(
                    {"eventName": _lambda.FilterRule.is_equal("INSERT")}
                )
            ]
        ))

        # DynamoDB Stream for Notifier (Trigger on MODIFY when score is added)
        # Note: In real world, we might separate tables or use EventBridge Pipes, 
        # but for simple portfolio, Stream is fine.
        notifier_fn.add_event_source(lambda_sources.DynamoEventSource(
            table,
            starting_position=_lambda.StartingPosition.TRIM_HORIZON,
            batch_size=1,
            filters=[
                _lambda.FilterCriteria.filter(
                    {
                        "eventName": _lambda.FilterRule.is_equal("MODIFY"),
                        "dynamodb": {
                            "NewImage": {
                                "status": {"S": _lambda.FilterRule.is_equal("MATCHED")}
                            }
                        }
                    }
                )
            ]
        ))
