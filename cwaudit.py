import boto3
import botocore
import csv
import sys

def extract_trailing_id(value):
    """Splits a string by '/' and returns the last element."""
    return value.split("/")[-1] if "/" in value else value

def audit_monitoring_resources(profile_name):
    session = boto3.Session(profile_name=profile_name)

    # Clients for EC2, RDS, ELBv2, and CloudWatch.
    ec2_client   = session.client('ec2')
    rds_client   = session.client('rds')
    elbv2_client = session.client('elbv2')
    cw_client    = session.client('cloudwatch')

    # -------------------------------------------------------------------------
    # 1. Collect Resources
    # -------------------------------------------------------------------------
    # EC2 Instances.
    ec2_response = ec2_client.describe_instances()
    ec2_resources = []
    for reservation in ec2_response.get("Reservations", []):
        for instance in reservation.get("Instances", []):
            instance_id   = instance.get("InstanceId", "N/A")
            instance_name = "N/A"
            for tag in instance.get("Tags", []):
                if tag.get("Key") == "Name":
                    instance_name = tag.get("Value")
                    break
            ec2_resources.append({
                "ResourceType": "EC2 Instance",
                "ResourceId": instance_id,
                "ResourceName": instance_name,
                "Alarms": []  # To be populated later.
            })

    # RDS Instances.
    rds_response = rds_client.describe_db_instances()
    rds_resources = []
    for db in rds_response.get("DBInstances", []):
        db_id = db.get("DBInstanceIdentifier", "N/A")
        rds_resources.append({
            "ResourceType": "RDS Instance",
            "ResourceId": db_id,
            "ResourceName": db_id,
            "Alarms": []
        })

    # Load Balancers.
    lb_response = elbv2_client.describe_load_balancers()
    lb_resources = []
    for lb in lb_response.get("LoadBalancers", []):
        lb_arn  = lb.get("LoadBalancerArn", "N/A")
        lb_name = lb.get("LoadBalancerName", "N/A")
        lb_resources.append({
            "ResourceType": "Load Balancer",
            "ResourceId": lb_arn,
            "ResourceName": lb_name,  # Use LB name from console.
            "Alarms": []
        })

    # Target Groups.
    tg_response = elbv2_client.describe_target_groups()
    tg_resources = []
    for tg in tg_response.get("TargetGroups", []):
        tg_arn  = tg.get("TargetGroupArn", "N/A")
        tg_name = tg.get("TargetGroupName", "N/A")
        tg_resources.append({
            "ResourceType": "Target Group",
            "ResourceId": tg_arn,
            "ResourceName": tg_name,  # Use TG name from console.
            "Alarms": []
        })

    # Combine all resources.
    all_resources = ec2_resources + rds_resources + lb_resources + tg_resources

    # -------------------------------------------------------------------------
    # 2. Retrieve CloudWatch Alarms and build a mapping from dimension keys
    #    to alarm names with their current state.
    # -------------------------------------------------------------------------
    alarm_data = []
    next_token = None
    while True:
        if next_token:
            resp = cw_client.describe_alarms(NextToken=next_token)
        else:
            resp = cw_client.describe_alarms()
        alarm_data.extend(resp.get("MetricAlarms", []))
        next_token = resp.get("NextToken")
        if not next_token:
            break

    # Compute counts of alarms by state.
    insufficient_count = sum(1 for alarm in alarm_data if alarm.get("StateValue") == "INSUFFICIENT_DATA")
    ok_count           = sum(1 for alarm in alarm_data if alarm.get("StateValue") == "OK")
    in_alarm_count     = sum(1 for alarm in alarm_data if alarm.get("StateValue") == "ALARM")

    # Calculate Total Alarms Configured as the sum of all three state counts.
    total_alarms_configured = insufficient_count + ok_count + in_alarm_count

    # Allowed keys for mapping.
    allowed_keys = ["InstanceId", "DBInstanceIdentifier", "LoadBalancer", "TargetGroup"]
    # Create nested mapping: for each allowed key, map a (parsed) dimension value -> set(alarm representations)
    alarm_mapping = { key: {} for key in allowed_keys }

    for alarm in alarm_data:
        alarm_name = alarm.get("AlarmName", "N/A")
        state      = alarm.get("StateValue", "N/A")
        alarm_repr = f"{alarm_name} ({state})"
        namespace  = alarm.get("Namespace", "")
        
        for dim in alarm.get("Dimensions", []):
            dim_name  = dim.get("Name", "")
            dim_value = dim.get("Value", "")
            if dim_name not in allowed_keys:
                continue
            # For any alarm with dimension "LoadBalancer" or "TargetGroup", always extract the trailing ID.
            if dim_name in ["LoadBalancer", "TargetGroup"]:
                parsed_value = extract_trailing_id(dim_value)
            else:
                parsed_value = dim_value

            if parsed_value not in alarm_mapping[dim_name]:
                alarm_mapping[dim_name][parsed_value] = set()
            alarm_mapping[dim_name][parsed_value].add(alarm_repr)

    # -------------------------------------------------------------------------
    # 3. Associate alarms with the collected resources.
    # -------------------------------------------------------------------------
    for resource in all_resources:
        rtype = resource["ResourceType"]
        alarms_set = set()
        if rtype == "EC2 Instance":
            alarms_set = alarms_set.union(alarm_mapping["InstanceId"].get(resource["ResourceId"], set()))
        elif rtype == "RDS Instance":
            alarms_set = alarms_set.union(alarm_mapping["DBInstanceIdentifier"].get(resource["ResourceId"], set()))
        elif rtype == "Load Balancer":
            # For load balancer, extract trailing id from its ARN.
            lb_id = extract_trailing_id(resource["ResourceId"])
            alarms_set = alarms_set.union(alarm_mapping["LoadBalancer"].get(lb_id, set()))
        elif rtype == "Target Group":
            # For target groups, extract trailing id from its ARN.
            tg_id = extract_trailing_id(resource["ResourceId"])
            alarms_set = alarms_set.union(alarm_mapping["TargetGroup"].get(tg_id, set()))
        
        if not alarms_set:
            resource["Alarms"] = ["No monitoring configured"]
        else:
            resource["Alarms"] = list(alarms_set)

    total_resources = len(all_resources)

    # -------------------------------------------------------------------------
    # 4. Write the output to CSV.
    # -------------------------------------------------------------------------
    with open("monitoring_audit.csv", "w", newline="") as f:
        writer = csv.writer(f)
        # Write top rows with summary counts.
        writer.writerow([f"Total Resources Audited: {total_resources}"])
        writer.writerow([f"Total Alarms Configured: {total_alarms_configured}"])
        writer.writerow([f"Total INSUFFICIENT_DATA Alarms: {insufficient_count}"])
        writer.writerow([f"Total OK Alarms: {ok_count}"])
        writer.writerow([f"Total ALARM Alarms: {in_alarm_count}"])
        # Write CSV header.
        writer.writerow(["Resource Type", "Resource ID", "Resource Name", "Alarms Configured"])
        for resource in all_resources:
            alarms_configured = ", ".join(sorted(resource["Alarms"]))
            writer.writerow([resource["ResourceType"], resource["ResourceId"], resource["ResourceName"], alarms_configured])

    print("Monitoring audit completed. Output saved to monitoring_audit.csv")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 cwaudit.py <AWS_PROFILE>")
        sys.exit(1)

    PROFILE_NAME = sys.argv[1]  # Get the profile name from the command-line argument
    try:
        audit_monitoring_resources(PROFILE_NAME)
    except botocore.exceptions.NoCredentialsError:
        print("No credentials found. Please ensure your profile is set up correctly in .aws/config.")
