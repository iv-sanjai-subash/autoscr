import boto3
import tabulate
from datetime import datetime
import logging

class AWSAccountAuditor:
    def __init__(self):
        """
        Initialize the auditor using read-only credentials for EC2 and CloudWatch.
        This setup is tailored for environments where only EC2-related read access is available.
        """
        self.session = boto3.Session()
        self.ec2_client = self.session.client('ec2')
        self.cloudwatch_client = self.session.client('cloudwatch')
        
        logging.basicConfig(
            filename=f'aws_audit_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def get_instance_name(self, instance):
        """
        Extract the "Name" tag from an instance's tags.
        If not available, return 'N/A'.
        """
        tags = instance.get('Tags', [])
        for tag in tags:
            if tag.get('Key') == 'Name':
                return tag.get('Value')
        return 'N/A'

    def audit_ec2_instances(self):
        """
        Audit EC2 instances and display their details.
        After printing a table of EC2 instance information, this method also retrieves all
        AMIs owned by your account and lists, for each one, the associated instance names and IDs.
        """
        try:
            # Retrieve EC2 instances.
            response = self.ec2_client.describe_instances()
            raw_instances = []  # Keep the raw instance data for later AMI mapping.
            instances_data = []  # For tabulated output.

            for reservation in response.get('Reservations', []):
                for instance in reservation.get('Instances', []):
                    raw_instances.append(instance)
                    
                    security_groups = [sg.get('GroupName') for sg in instance.get('SecurityGroups', [])]
                    instance_data = {
                        'Instance ID': instance.get('InstanceId', 'N/A'),
                        'Name': self.get_instance_name(instance),
                        'Type': instance.get('InstanceType', 'N/A'),
                        'State': instance.get('State', {}).get('Name', 'N/A'),
                        'Public IP': instance.get('PublicIpAddress', 'N/A'),
                        'Private IP': instance.get('PrivateIpAddress', 'N/A'),
                        'Security Groups': ', '.join(security_groups) if security_groups else 'N/A',
                        'IAM Role': instance.get('IamInstanceProfile', {}).get('Arn', 'N/A')
                    }

                    # Retrieve CloudWatch metrics (e.g., available alarms) for the instance.
                    metrics_response = self.cloudwatch_client.list_metrics(
                        Namespace='AWS/EC2',
                        Dimensions=[{'Name': 'InstanceId', 'Value': instance.get('InstanceId', 'N/A')}]
                    )
                    alarms = [metric.get('MetricName') for metric in metrics_response.get('Metrics', [])]
                    instance_data['Monitoring Alarms'] = ', '.join(alarms) if alarms else 'None'

                    instances_data.append(instance_data)

            # Display the EC2 Instances Audit table.
            ec2_headers = [
                'Instance ID', 'Name', 'Type', 'State', 'Public IP', 
                'Private IP', 'Security Groups', 'IAM Role', 'Monitoring Alarms'
            ]
            print("\nEC2 Instances Audit Results:")
            print(tabulate.tabulate(instances_data, headers=ec2_headers, tablefmt='grid'))
            
            # Build a mapping from AMI IDs to the instances that were launched from them.
            instance_mapping = {}
            for instance in raw_instances:
                ami_id = instance.get('ImageId')
                if ami_id:
                    instance_str = f"{self.get_instance_name(instance)} ({instance.get('InstanceId', 'N/A')})"
                    instance_mapping.setdefault(ami_id, []).append(instance_str)

            # Retrieve all AMIs owned by your account.
            images_response = self.ec2_client.describe_images(Owners=['self'])
            images_data = images_response.get('Images', [])
            ami_results = []
            for image in images_data:
                ami_id = image.get('ImageId', 'N/A')
                ami_name = image.get('Name', 'N/A')
                associated_instances = instance_mapping.get(ami_id)
                instances_str = ", ".join(associated_instances) if associated_instances else "None"
                
                ami_results.append({
                    'AMI ID': ami_id,
                    'AMI Name': ami_name,
                    'Instances': instances_str
                })

            # Display the AMI Audit table.
            ami_headers = ['AMI ID', 'AMI Name', 'Instances']
            print("\nAMI Audit Results (AMI and Associated Instances):")
            print(tabulate.tabulate(ami_results, headers=ami_headers, tablefmt='grid'))
            
        except Exception as e:
            logging.error(f"Error auditing EC2 instances: {str(e)}")
            print("Error: Unable to retrieve EC2 instance or AMI information. Please check your IAM permissions.")

def main():
    auditor = AWSAccountAuditor()
    
    while True:
        print("\n=== AWS EC2 Account Auditor ===")
        print("1. Audit EC2 Instances (including AMI association)")
        print("2. Exit")
        
        choice = input("\nEnter your choice (1-2): ").strip()
        
        if choice == '1':
            auditor.audit_ec2_instances()
        elif choice == '2':
            print("Thank you for using AWS EC2 Account Auditor!")
            break
        else:
            print("Invalid choice. Please select a valid option.")

if __name__ == '__main__':
    main()
