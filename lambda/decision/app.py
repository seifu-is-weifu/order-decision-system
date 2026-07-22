import os
import logging
from datetime import datetime, UTC
from decimal import Decimal

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# DynamoDB connection
dynamodb = boto3.resource("dynamodb")

customers_table = dynamodb.Table(os.environ["CUSTOMERS_TABLE"])
orders_table = dynamodb.Table(os.environ["ORDERS_TABLE"])
inventory_table = dynamodb.Table(os.environ["INVENTORY_TABLE"])


def get_string(image, field):
    """Safely read a string value from a DynamoDB Stream image."""
    return image[field]["S"]


def get_number(image, field):
    """Safely read a numeric value from a DynamoDB Stream image."""
    return Decimal(image[field]["N"])


def determine_decision(
    basket_value,
    fraud_score,
    payment_attempts,
    customer,
    inventory,
):
    """
    Apply the business rules and return:

    decision
    decision_reason
    """

    stock = int(inventory["stock"])
    tenure = int(customer["customerTenureDays"])
    lifetime_value = int(customer["lifetimeValue"])

    # Rule 1
    if stock <= 0:
        return (
            "DECLINED",
            "Product is out of stock",
        )

    # Rule 2
    if fraud_score >= 90:
        return (
            "DECLINED",
            "Extremely high fraud score",
        )
        # Rule 3
    if fraud_score >= 75 and basket_value > 1000:
        return (
            "MANUAL_REVIEW",
            "High fraud score on expensive order",
        )

    # Rule 4
    if payment_attempts >= 4:
        return (
            "MANUAL_REVIEW",
            "Too many payment attempts",
        )

    # Rule 5
    if tenure < 30 and basket_value > 2000:
        return (
            "MANUAL_REVIEW",
            "Large order from a new customer",
        )

    # Rule 6
    if lifetime_value >= 10000 and fraud_score < 30:
        return (
            "APPROVED",
            "Trusted high-value customer",
        )

    # Default
    return (
        "APPROVED",
        "Passed all automated checks",
    )


def lambda_handler(event, context):
    logger.info("Received %d stream records", len(event["Records"]))

    for record in event["Records"]:

        # Only process newly created orders
        if record["eventName"] != "INSERT":
            continue

        image = record["dynamodb"]["NewImage"]

        order_id = get_string(image, "orderId")
        customer_id = get_string(image, "customerId")
        sku = get_string(image, "sku")

        basket_value = float(get_number(image, "basketValue"))
        fraud_score = int(get_number(image, "fraudScore"))
        payment_attempts = int(get_number(image, "paymentAttempts"))

        logger.info("Processing order %s", order_id)

        # Skip if this order has already been processed.
        current_decision = get_string(image, "decision")
        if current_decision != "PENDING":
            logger.info(
                "Skipping order %s because decision is already %s",
                order_id,
                current_decision,
            )
            continue

        # Read customer
        customer_response = customers_table.get_item(
            Key={
                "customerId": customer_id,
            }
        )

        customer = customer_response.get("Item")

        if customer is None:
            logger.error(
                "Customer %s not found",
                customer_id,
            )
            continue

        # Read inventory
        inventory_response = inventory_table.get_item(
            Key={
                "sku": sku,
            }
        )

        inventory = inventory_response.get("Item")

        if inventory is None:
            logger.error(
                "Inventory item %s not found",
                sku,
            )
            continue

        decision, reason = determine_decision(
            basket_value,
            fraud_score,
            payment_attempts,
            customer,
            inventory,
        )

        logger.info(
            "Decision for %s: %s (%s)",
            order_id,
            decision,
            reason,
        )

        try:
            orders_table.update_item(
                Key={
                    "orderId": order_id,
                },
                UpdateExpression="""
                    SET
                        #decision = :decision,
                        decisionReason = :reason,
                        decisionTimestamp = :timestamp,
                        decisionVersion = :version,
                        downstreamStatus = :downstream
                """,
                ConditionExpression="#decision = :pending",
                ExpressionAttributeNames={
                    "#decision": "decision",
                },
                ExpressionAttributeValues={
                    ":decision": decision,
                    ":pending": "PENDING",
                    ":reason": reason,
                    ":timestamp": datetime.now(UTC).isoformat(),
                    ":version": Decimal("1"),
                    ":downstream": "PENDING",
                },
            )

            logger.info(
                "Successfully updated order %s with decision %s",
                order_id,
                decision,
            )

        except Exception:
            logger.exception(
                "Failed to update order %s",
                order_id,
            )

    return {
        "statusCode": 200,
        "processedRecords": len(event["Records"]),
    }
