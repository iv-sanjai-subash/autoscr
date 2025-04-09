import boto3
import botocore
import datetime

def get_age_from_dt(dt):
    """
    Given a datetime object, compute a human-friendly age.
    Returns strings like "15 days old", "2 months old", or "1 years old".
    """
    # Ensure dt is timezone aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    now = datetime.datetime.now(datetime.timezone.utc)
    delta = now - dt
    days = delta.days
    if days < 30:
        return f"{days} days old"
    elif days < 365:
        months = days // 30
        return f"{months} months old"
    else:
        years = days // 365
        return f"{years} years old"

def audit_ec2_resources(profile_name):
    # Create a boto3 session using the specified read-only profile.
    session = boto3.Session(profile_name=profile_name)
    ec2_client = session.client('ec2')

    # ----------------------- EC2 Instances ---------------------------
    # Retrieve instances and build a mapping of instance_id -> instance name.
    ec2_response = ec2_client.describe_instances()
    instance_name_map = {}
    ec2_instances = []
    instance_ami_usage = {}

    for reservation in ec2_response['Reservations']:
        for instance in reservation['Instances']:
            instance_id = instance.get('InstanceId', 'N/A')
            # Safely extract the instance Name tag if available
            name = next((tag.get('Value') for tag in instance.get('Tags', []) if tag.get('Key') == 'Name'), "N/A")
            # Platform will be 'Windows' if present; otherwise, we default to Linux.
            platform = instance.get('Platform', 'Linux')
            attached_vols = [
                bdm['Ebs']['VolumeId'] 
                for bdm in instance.get('BlockDeviceMappings', []) if 'Ebs' in bdm
            ]
            instance_name_map[instance_id] = name
            image_id = instance.get('ImageId', 'N/A')
            instance_ami_usage.setdefault(image_id, []).append(instance_id)
            ec2_instances.append({
                "Name": name,
                "InstanceId": instance_id,
                "Platform": platform,
                "AttachedVolumes": ", ".join(attached_vols) if attached_vols else "None"
            })

    # Print EC2 Instances
    print("===== EC2 Instances =====")
    header_ec2 = "{:<25} {:<25} {:<10} {:<40}".format("Name", "Instance ID", "Platform", "Attached Volumes")
    print(header_ec2)
    print("-" * len(header_ec2))
    for inst in ec2_instances:
        print("{:<25} {:<25} {:<10} {:<40}".format(
            inst["Name"], inst["InstanceId"], inst["Platform"], inst["AttachedVolumes"]
        ))
    print()

    # ----------------------- AMIs (Owned by Self) ---------------------------
    images_response = ec2_client.describe_images(Owners=['self'])
    ami_list = []
    for image in images_response['Images']:
        ami_id = image.get('ImageId', 'N/A')
        ami_name = image.get('Name', 'N/A')
        creation_date_str = image.get('CreationDate')
        try:
            # Try parsing with microseconds first
            creation_dt = datetime.datetime.strptime(creation_date_str, "%Y-%m-%dT%H:%M:%S.%fZ")
        except ValueError:
            creation_dt = datetime.datetime.strptime(creation_date_str, "%Y-%m-%dT%H:%M:%SZ")
        age = get_age_from_dt(creation_dt)
        # Build a string for added tags: key=value pairs separated by commas
        added_tags = ", ".join([f"{tag.get('Key')}={tag.get('Value')}" for tag in image.get('Tags', [])]) if image.get('Tags') else "None"
        ami_list.append({
            "AMI_ID": ami_id,
            "AMI_Name": ami_name,
            "Age": age,
            "CreationDT": creation_dt,  # for sorting
            "AddedTags": added_tags
        })
    # Sort AMIs with newest first based on creation date
    ami_list = sorted(ami_list, key=lambda x: x["CreationDT"], reverse=True)
    print(f"===== AMIs ===== - total number of AMI's: {len(ami_list)}")
    header_ami = "{:<25} {:<35} {:<20} {:<40}".format("AMI ID", "AMI Name", "Age (newest first)", "added tags")
    print(header_ami)
    print("-" * len(header_ami))
    for ami in ami_list:
        print("{:<25} {:<35} {:<20} {:<40}".format(
            ami["AMI_ID"], ami["AMI_Name"], ami["Age"], ami["AddedTags"]
        ))
    print()

    # ----------------------- EBS Volumes ---------------------------
    volumes_response = ec2_client.describe_volumes()
    volume_list = []
    for volume in volumes_response['Volumes']:
        vol_id = volume.get('VolumeId', 'N/A')
        # Check for a 'backup' tag (case-insensitive)
        backup_status = next(
            (tag.get('Value') for tag in volume.get('Tags', []) if tag.get('Key', '').lower() == 'backup'),
            "No Backup Tag"
        )
        attachments = volume.get('Attachments', [])
        attached_instance = attachments[0]['InstanceId'] if attachments else "Not Attached"
        instance_name = instance_name_map.get(attached_instance, "N/A") if attached_instance != "Not Attached" else "N/A"
        volume_list.append({
            "VolumeID": vol_id,
            "AttachedInstance": attached_instance,
            "InstanceName": instance_name,
            "BackupStatus": backup_status
        })
    print(f"===== EBS Volumes ===== - total number of volumes: {len(volume_list)}")
    header_vol = "{:<25} {:<25} {:<25} {:<20}".format("Volume ID", "Attached Instance", "Instance Name", "Backup Status")
    print(header_vol)
    print("-" * len(header_vol))
    for vol in volume_list:
        print("{:<25} {:<25} {:<25} {:<20}".format(
            vol["VolumeID"], vol["AttachedInstance"], vol["InstanceName"], vol["BackupStatus"]
        ))
    print()

    # ----------------------- EBS Snapshots ---------------------------
    snapshots_response = ec2_client.describe_snapshots(OwnerIds=['self'])
    snapshot_list = []
    for snapshot in snapshots_response['Snapshots']:
        snapshot_id = snapshot.get('SnapshotId', 'N/A')
        volume_id = snapshot.get('VolumeId', 'N/A')
        start_time = snapshot.get('StartTime')  # This is already a datetime object
        age = get_age_from_dt(start_time)
        # Try to get a 'CreatedBy' tag if it exists (case-insensitive)
        created_by = next(
            (tag.get('Value') for tag in snapshot.get('Tags', []) if tag.get('Key', '').lower() == 'createdby'),
            "N/A"
        )
        snapshot_list.append({
            "SnapshotID": snapshot_id,
            "VolumeID": volume_id,
            "Age": age,
            "StartTime": start_time,  # for sorting
            "CreatedBy": created_by
        })
    # Sort snapshots: newest first based on StartTime
    snapshot_list = sorted(snapshot_list, key=lambda x: x["StartTime"], reverse=True)
    print(f"===== EBS snapshots ===== - total number of snapshots: {len(snapshot_list)}")
    header_snap = "{:<25} {:<25} {:<25} {:<20}".format("snapshot ID", "Attached volume", "age (newest first)", "created by")
    print(header_snap)
    print("-" * len(header_snap))
    for snap in snapshot_list:
        print("{:<25} {:<25} {:<25} {:<20}".format(
            snap["SnapshotID"], snap["VolumeID"], snap["Age"], snap["CreatedBy"]
        ))

if __name__ == "__main__":
    PROFILE_NAME = "audit-readonly"  # Replace with your AWS profile name from .aws/config
    try:
        audit_ec2_resources(PROFILE_NAME)
    except botocore.exceptions.NoCredentialsError:
        print("No credentials found. Please ensure your profile is set up correctly in .aws/config.")

