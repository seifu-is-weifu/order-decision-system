import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';

import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as lambdaEventSources from 'aws-cdk-lib/aws-lambda-event-sources';

import * as logs from 'aws-cdk-lib/aws-logs';


export class InfrastructureStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const customersTable = new dynamodb.Table(this, 'CustomersTable', {
      tableName: 'Customers',

      partitionKey: {
        name: 'customerId',
        type: dynamodb.AttributeType.STRING,
      },

      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,

      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    const ordersTable = new dynamodb.Table(this, 'OrdersTable', {
      tableName: 'Orders',

      partitionKey: {
        name: 'orderId',
        type: dynamodb.AttributeType.STRING,
      },

      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,

      stream: dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,

      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    const inventoryTable = new dynamodb.Table(this, 'InventoryTable', {
      tableName: 'Inventory',

      partitionKey: {
        name: 'sku',
        type: dynamodb.AttributeType.STRING,
      },

      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,

      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    const decisionLambda = new lambda.Function(this, 'DecisionLambda', {
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'app.lambda_handler',
      code: lambda.Code.fromAsset('../lambda/decision'),
      timeout: cdk.Duration.seconds(30),
      environment: {
        CUSTOMERS_TABLE: customersTable.tableName,
        ORDERS_TABLE: ordersTable.tableName,
        INVENTORY_TABLE: inventoryTable.tableName,
      },
      logRetention: logs.RetentionDays.ONE_WEEK,
      tracing: lambda.Tracing.ACTIVE,
      description: "Evaluates incoming orders and writes approval decisions",
    });

    customersTable.grantReadData(decisionLambda);
    inventoryTable.grantReadData(decisionLambda);
    ordersTable.grantReadWriteData(decisionLambda);

    decisionLambda.addEventSource(
      new lambdaEventSources.DynamoEventSource(ordersTable, {
        startingPosition: lambda.StartingPosition.LATEST,
        batchSize: 1,
        retryAttempts: 2,
      }),
    );

    const downstreamLambda = new lambda.Function(this, 'DownstreamLambda', {
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'app.lambda_handler',
      code: lambda.Code.fromAsset('../lambda/downstream'),
      timeout: cdk.Duration.seconds(30),
      environment: {
        ORDERS_TABLE: ordersTable.tableName,
      },
      logRetention: logs.RetentionDays.ONE_WEEK,
      tracing: lambda.Tracing.ACTIVE,
      description: "Processes completed decisions and performs downstream routing",
    });

    ordersTable.grantReadWriteData(downstreamLambda);

    downstreamLambda.addEventSource(
      new lambdaEventSources.DynamoEventSource(ordersTable, {
        startingPosition: lambda.StartingPosition.LATEST,
        batchSize: 1,
        retryAttempts: 2,
      }),
    );

    new cdk.CfnOutput(this, 'OrdersTableName', {
      value: ordersTable.tableName,
    });

    new cdk.CfnOutput(this, 'CustomersTableName', {
      value: customersTable.tableName,
    });

    new cdk.CfnOutput(this, 'InventoryTableName', {
      value: inventoryTable.tableName,
    });

  }
}
