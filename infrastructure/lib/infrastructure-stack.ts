import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';


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

  }
}
