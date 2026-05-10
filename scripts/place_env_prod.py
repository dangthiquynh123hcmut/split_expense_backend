#!/usr/bin/env python
"""Place .env.prod onto all EC2 instances in the ASG via SSM Send Command."""

import base64
import os
import sys
import time

import boto3


REGION = "ap-southeast-1"
ASG_NAME = "split-expense-asg"
ENV_FILE = os.path.join(os.path.dirname(__file__), "..", "env", ".env.prod")
DEST_PATH = "/opt/split-expense-backend/env/.env.prod"


def main():
    print("=== [1/3] Loading .env.prod ===")
    with open(ENV_FILE, "rb") as f:
        env_bytes = f.read()
    env_b64 = base64.b64encode(env_bytes).decode("utf-8")
    print(f"  File size: {len(env_bytes)} bytes, base64 length: {len(env_b64)}")

    print("\n=== [2/3] Getting instance IDs from ASG ===")
    ec2 = boto3.client("ec2", region_name=REGION)
    resp = ec2.describe_instances(
        Filters=[
            {"Name": "tag:aws:autoscaling:groupName", "Values": [ASG_NAME]},
            {"Name": "instance-state-name", "Values": ["running"]},
        ]
    )
    instance_ids = [
        i["InstanceId"] for r in resp["Reservations"] for i in r["Instances"]
    ]
    if not instance_ids:
        print("ERROR: No running instances found in ASG!")
        sys.exit(1)
    print(f"  Found {len(instance_ids)} instances: {', '.join(instance_ids)}")

    print("\n=== [3/3] Sending .env.prod via SSM ===")
    ssm = boto3.client("ssm", region_name=REGION)

    commands = [
        "mkdir -p /opt/split-expense-backend/env",
        f"echo '{env_b64}' | base64 -d > {DEST_PATH}",
        f"chmod 600 {DEST_PATH}",
        f"chown root:root {DEST_PATH}",
        f"echo 'Done. Lines:' $(wc -l < {DEST_PATH})",
    ]

    for instance_id in instance_ids:
        print(f"\n  -> {instance_id} ...")
        resp = ssm.send_command(
            InstanceIds=[instance_id],
            DocumentName="AWS-RunShellScript",
            Parameters={"commands": commands},
        )
        cmd_id = resp["Command"]["CommandId"]
        print(f"     CommandId: {cmd_id}")

        # Wait for completion (up to 60s)
        for attempt in range(20):
            time.sleep(4)
            try:
                inv = ssm.get_command_invocation(
                    CommandId=cmd_id,
                    InstanceId=instance_id,
                )
                status = inv["Status"]
                if status in ("Success", "Failed", "Cancelled", "TimedOut"):
                    break
            except ssm.exceptions.InvocationDoesNotExist:
                pass

        if status == "Success":
            print("     [OK] .env.prod placed successfully")
            stdout = inv.get("StandardOutputContent", "").strip()
            if stdout:
                print(f"     Output: {stdout}")
        else:
            print(f"     [FAIL] Status: {status}")
            print(f"     STDOUT: {inv.get('StandardOutputContent', '')}")
            print(f"     STDERR: {inv.get('StandardErrorContent', '')}")

    print("\n=== Done! ===")
    print("Next: git push origin main to trigger CI/CD pipeline")


if __name__ == "__main__":
    main()
