# Order Decision System (AWS Free Tier)

## Overview

This project is an event-driven order processing system built entirely on AWS Free Tier services.

When a new order is created, AWS automatically evaluates it using business rules and then performs a downstream operational action.

The entire solution is deployed using AWS CDK and follows a serverless architecture.

---

## Architecture

The system consists of three DynamoDB tables:

* Customers
* Orders
* Inventory

Two AWS Lambda functions process the data:

### Decision Lambda

Triggered by DynamoDB Streams whenever a new order is inserted.

The function reads information from:

* Orders
* Customers
* Inventory

It evaluates multiple independent business rules including:

* Fraud score
* Basket value
* Customer tenure
* Customer lifetime value
* Payment attempts
* Inventory availability

The Lambda writes back:

* decision
* decisionReason
* decisionTimestamp
* decisionVersion
* downstreamStatus

---

### Downstream Lambda

Triggered whenever an order decision is written.

Depending on the decision, it performs a downstream action.

Examples:

| Decision      | Downstream Action |
| ------------- | ----------------- |
| APPROVED      | FULFILMENT_QUEUED |
| MANUAL_REVIEW | ESCALATED         |
| DECLINED      | CLOSED            |

The Lambda updates:

* downstreamAction
* downstreamStatus
* downstreamTimestamp

---

## Architecture Flow

New Order

↓

Orders Table

↓

DynamoDB Stream

↓

Decision Lambda

↓

Orders Table Updated

↓

DynamoDB Stream

↓

Downstream Lambda

↓

Final Order State

---

## Why DynamoDB?

DynamoDB was selected because it best fits the required access pattern.

Advantages:

* Pay-per-request pricing keeps the project inside AWS Free Tier.
* Very low latency lookups for customer and inventory records.
* Native DynamoDB Streams eliminate the need for polling.
* Fully managed service with no server administration.
* Excellent fit for event-driven architectures.

Alternative options considered:

* Amazon RDS would require database administration and higher operational overhead.
* Amazon S3 + Athena is well suited for analytics but not for low-latency transactional lookups.

---

## Dummy Dataset

The seed script generates more than 100,000 realistic records.

The dataset includes:

* Customers
* Orders
* Inventory

Characteristics include:

* Long-tail customer value distribution
* New and long-term customers
* Multiple payment methods
* High-value purchases
* Fraud-shaped anomalies
* Inventory variation
* Different payment attempt counts

---

## Business Decision Rules

Orders are evaluated using multiple independent signals.

Current rules include:

* Inventory availability
* Fraud score
* Basket value
* Customer tenure
* Customer lifetime value
* Payment attempts

Possible outcomes:

* APPROVED
* MANUAL_REVIEW
* DECLINED

---

## Technologies

* AWS CDK
* AWS Lambda
* Amazon DynamoDB
* DynamoDB Streams
* Python 3.12
* TypeScript
* Boto3

---

## Deployment

Install dependencies:

```bash
npm install
```

Deploy infrastructure:

```bash
cd infrastructure
npm install
cdk deploy
```

Generate sample data:

```bash
python3 seed/generate_data.py
```

---

## Testing

Insert a new order:

```bash
aws dynamodb put-item ...
```

The pipeline automatically:

1. Evaluates the order.
2. Writes a decision.
3. Triggers downstream processing.
4. Updates the order status.

---

## Cost Estimate

The solution stays comfortably within AWS Free Tier.

Primary services used:

* DynamoDB (On-Demand)
* AWS Lambda
* DynamoDB Streams
* CloudWatch Logs

For a demonstration workload, expected monthly cost is effectively $0 while within Free Tier limits.

---

## Cleanup

To remove all AWS resources:

```bash
cd infrastructure
cdk destroy
```

---

## Future Improvements

Given additional time, the following enhancements would be implemented:

* Amazon SQS dead-letter queue for failed events
* CloudWatch alarms and dashboards
* EventBridge integration
* API Gateway for external order submission
* CI/CD using GitHub Actions
* Unit and integration testing
* IAM permission hardening
* Metrics and tracing dashboards
* Multi-region disaster recovery
* Additional fraud detection using machine learning
