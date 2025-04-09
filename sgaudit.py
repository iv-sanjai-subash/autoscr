import boto3
import botocore
import csv
import sys

def audit_security_groups(profile_name):
    # Create a session using the specified AWS profile.
    session = boto3.Session(profile_name=profile_name)
    ec2_client = session.client('ec2')

    # Retrieve all security groups.
    sg_response = ec2_client.describe_security_groups()
    security_groups = sg_response['SecurityGroups']

    # Retrieve all EC2 instances and build a mapping from security group ID to instance details.
    instances_response = ec2_client.describe_instances()
    sg_instance_map = {}  # key: security group id; value: list of tuples (instance_id, instance_name)
    for reservation in instances_response.get('Reservations', []):
        for instance in reservation.get('Instances', []):
            instance_id = instance.get('InstanceId', 'N/A')
            instance_name = 'N/A'
            for tag in instance.get('Tags', []):
                if tag.get('Key') == 'Name':
                    instance_name = tag.get('Value', 'N/A')
                    break
            for sg in instance.get('SecurityGroups', []):
                sg_id = sg.get('GroupId')
                if sg_id:
                    if sg_id not in sg_instance_map:
                        sg_instance_map[sg_id] = []
                    sg_instance_map[sg_id].append((instance_id, instance_name))

    # Save the audit output to a CSV file.
    with open('security_audit.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        # Write a row with the total count of security groups.
        writer.writerow([f"Total Security Groups: {len(security_groups)}"])
        # Write the CSV header row.
        writer.writerow(["Security Group ID", "Security Group Name", "Instance ID", "Instance Name",
                         "Direction", "Protocol", "From Port", "To Port", "CIDR", "Description"])
        
        # Process only inbound (IpPermissions) rules.
        for sg in security_groups:
            sg_id = sg.get("GroupId", "N/A")
            sg_name = sg.get("GroupName", "N/A")
            # Get associated instance details; if none, default to ("N/A", "N/A").
            attached_instances = sg_instance_map.get(sg_id, [("N/A", "N/A")])
            for rule in sg.get("IpPermissions", []):
                protocol = rule.get("IpProtocol", "N/A")
                from_port = rule.get("FromPort", "N/A")
                to_port = rule.get("ToPort", "N/A")
                for ip_range in rule.get("IpRanges", []):
                    cidr = ip_range.get("CidrIp", "")
                    if cidr == "0.0.0.0/0":
                        description = ip_range.get("Description", "")
                        for instance_id, instance_name in attached_instances:
                            writer.writerow([sg_id, sg_name, instance_id, instance_name,
                                             "Ingress", protocol, from_port, to_port, cidr, description])
    
    print("Security audit completed. Output saved to security_audit.csv")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 sgaudit.py <AWS_PROFILE>")
        sys.exit(1)

    PROFILE_NAME = sys.argv[1]  # Get the profile name from the command-line argument
    try:
        audit_security_groups(PROFILE_NAME)
    except botocore.exceptions.NoCredentialsError:
        print("No credentials found. Please ensure your profile is set up correctly in .aws/config.")
