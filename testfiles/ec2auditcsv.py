import boto3
import botocore
import datetime
import csv

def get_age_from_dt(dt):
    """
    Given a datetime object, compute a human-friendly age.
    Returns strings like "15 days old", "2 months old", or "1 years old".
    """
    # Ensure the datetime has timezone info
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
    ec2_response = ec2_client.describe_instances()
    instance_name_map = {}
    ec2_instances = []
    instance_ami_usage = {}
    
    for reservation in ec2_response['Reservations']:
        for instance in reservation['Instances']:
            instance_id = instance.get('InstanceId', 'N/A')
            # Get instance name from tags if available
            name = next((tag.get('Value') for tag in instance.get('Tags', []) if tag.get('Key') == 'Name'), "N/A")
            # If 'Platform' exists then it's Windows; otherwise, assume Linux
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

    # ----------------------- AMIs (Owned by Self) ---------------------------
    images_response = ec2_client.describe_images(Owners=['self'])
    ami_list = []
    for image in images_response['Images']:
        ami_id = image.get('ImageId', 'N/A')
        ami_name = image.get('Name', 'N/A')
        creation_date_str = image.get('CreationDate')
        try:
            # Parse creation date with microseconds first
            creation_dt = datetime.datetime.strptime(creation_date_str, "%Y-%m-%dT%H:%M:%S.%fZ")
        except ValueError:
            creation_dt = datetime.datetime.strptime(creation_date_str, "%Y-%m-%dT%H:%M:%SZ")
        age = get_age_from_dt(creation_dt)
        added_tags = ", ".join([f"{tag.get('Key')}={tag.get('Value')}" for tag in image.get('Tags', [])]) if image.get('Tags') else "None"
        ami_list.append({
            "AMI_ID": ami_id,
            "AMI_Name": ami_name,
            "Age": age,
            "CreationDT": creation_dt,  # for sorting
            "AddedTags": added_tags
        })
    # Sort AMIs: newest first
    ami_list = sorted(ami_list, key=lambda x: x["CreationDT"], reverse=True)

    # ----------------------- EBS Volumes ---------------------------
    volumes_response = ec2_client.describe_volumes()
    volume_list = []
    for volume in volumes_response['Volumes']:
        vol_id = volume.get('VolumeId', 'N/A')
        # Get backup tag (if any) – case insensitive search for key 'backup'
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

    # ----------------------- EBS Snapshots ---------------------------
    snapshots_response = ec2_client.describe_snapshots(OwnerIds=['self'])
    snapshot_list = []
    for snapshot in snapshots_response['Snapshots']:
        snapshot_id = snapshot.get('SnapshotId', 'N/A')
        volume_id = snapshot.get('VolumeId', 'N/A')
        start_time = snapshot.get('StartTime')  # Already a datetime object
        age = get_age_from_dt(start_time)
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
    # Sort snapshots: newest first
    snapshot_list = sorted(snapshot_list, key=lambda x: x["StartTime"], reverse=True)

    # ----------------------- Save to CSV Files ---------------------------
    # Save EC2 Instances
    with open('ec2_instances.csv', 'w', newline='') as f_ec2:
        writer = csv.writer(f_ec2)
        writer.writerow(["Name", "Instance ID", "Platform", "Attached Volumes"])
        for inst in ec2_instances:
            writer.writerow([inst["Name"], inst["InstanceId"], inst["Platform"], inst["AttachedVolumes"]])
    
    # Save AMIs
    with open('amis.csv', 'w', newline='') as f_ami:
        writer = csv.writer(f_ami)
        writer.writerow(["AMI ID", "AMI Name", "Age (newest first)", "added tags"])
        for ami in ami_list:
            writer.writerow([ami["AMI_ID"], ami["AMI_Name"], ami["Age"], ami["AddedTags"]])
    
    # Save EBS Volumes
    with open('ebs_volumes.csv', 'w', newline='') as f_vol:
        writer = csv.writer(f_vol)
        writer.writerow(["Volume ID", "Attached Instance", "Instance Name", "Backup Status"])
        for vol in volume_list:
            writer.writerow([vol["VolumeID"], vol["AttachedInstance"], vol["InstanceName"], vol["BackupStatus"]])
    
    # Save EBS Snapshots
    with open('ebs_snapshots.csv', 'w', newline='') as f_snap:
        writer = csv.writer(f_snap)
        writer.writerow(["Snapshot ID", "Attached volume", "Age (newest first)", "created by"])
        for snap in snapshot_list:
            writer.writerow([snap["SnapshotID"], snap["VolumeID"], snap["Age"], snap["CreatedBy"]])
    
    print("Output saved to CSV files:")
    print("  ec2_instances.csv")
    print("  amis.csv")
    print("  ebs_volumes.csv")
    print("  ebs_snapshots.csv")

if __name__ == "__main__":
    PROFILE_NAME = "audit-readonly"  # Replace with your AWS profile name from .aws/config
    try:
        audit_ec2_resources(PROFILE_NAME)
    except botocore.exceptions.NoCredentialsError:
        print("No credentials found. Please ensure your profile is set up correctly in .aws/config.")

