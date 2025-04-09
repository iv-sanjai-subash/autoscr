import boto3

def delete_snapshots(profile_name, snapshot_ids):
    # Use the specified AWS profile
    session = boto3.Session(profile_name=profile_name)
    ec2 = session.client('ec2')

    for snapshot_id in snapshot_ids:
        try:
            print(f"Deleting snapshot: {snapshot_id}")
            ec2.delete_snapshot(SnapshotId=snapshot_id)
            print(f"Successfully deleted snapshot: {snapshot_id}")
        except Exception as e:
            print(f"Failed to delete snapshot {snapshot_id}: {e}")

def main():
    profile_name = input("Enter your AWS profile name: ")
    # List of snapshots to delete
    snapshots_to_delete = [
        'snap-0162e45f9c472255c', 'snap-029840d8b64773e3b', 'snap-01ad6d8fd0ebed09a', 
        'snap-04abe0c9fb65f99b5', 'snap-00db5a52e43751ef1', 'snap-0d5348a443a521177', 
        'snap-04173a0b034290a4c', 'snap-084b8923232c02e7f', 'snap-043a2c5f0562e5ecc',
        'snap-04a92edc0425bcb2f', 'snap-04567462fe8edf6c1', 'snap-0baf0c79cdfd4e3f7',
        'snap-0b29dbffbe8062767', 'snap-0d6b04a8ee1eb4b6f', 'snap-03a7a0dc8c1e171c8',
        'snap-07b7beaa2f60d19ad', 'snap-075b7fd10f39453b1', 'snap-04e4173a069d63ca1',
        'snap-079f49a286319420e', 'snap-00aec5d89f1088413', 'snap-0692912efd3f61b5c',
        'snap-0c1e7b3fad494015f', 'snap-0ae3d69794b45038a', 'snap-0cae450fd95ea5b43',
        'snap-0a1f9bcb995affdc0', 'snap-0634934fbec95351a', 'snap-0b218ff336428a4ca',
        'snap-0a2e43b0982b974bf', 'snap-0ca5c3247ac1b362c', 'snap-0c3ea96fb813fa1a9',
        'snap-0a5acae6d7019ff83', 'snap-050beaaf121e287ea', 'snap-0dc7747ffebcb45c7',
        'snap-0f921ebda3fe1a955', 'snap-0cb250985056aac2e', 'snap-0eebf8cf156af9cd3',
        'snap-0daf8e942ddd8140f', 'snap-07c627164ad952914', 'snap-02db6cce36a71d7f9',
        'snap-0569b06df72d1cfb2', 'snap-0017674994afdbce8', 'snap-073128479cb1ba094',
        'snap-09ccd3560d92d5bc7', 'snap-0dadb152259fd6823', 'snap-0570f9c3cefcbb282',
        'snap-01c9d40049172630c', 'snap-0d776cc49ef190930', 'snap-06fb820a18a1b047e',
        'snap-024718af6ecd136e3', 'snap-0b601789896c90094', 'snap-05af833babb2f0623',
        'snap-0c378210287c662e7', 'snap-0ddb2a3937e8ff36f', 'snap-0e9baa86e8d8a9be9',
        'snap-0b106503274c5a6fe', 'snap-0822b4b3ccc8a0766', 'snap-0dfbe38f2abb3f419',
        'snap-0dcbd10143328df6b', 'snap-040f70936cd52cefc', 'snap-0eab976e8e10c28b0',
        'snap-0934d854d773ff3b6', 'snap-010db29853e27dfd0', 'snap-05af933402f066ffa',
        'snap-0cba3bb62d4837a25', 'snap-018ed466fb1a957e2', 'snap-07f98b6caf1aa2312',
        'snap-0d745b68c909e50a4', 'snap-030405a8176c70f18', 'snap-06e21e155fd5dbe0e',
        'snap-0d833e3cbdd4d6e04', 'snap-01192851c0aa1306f', 'snap-07e0796ea27178254',
        'snap-0f76dc1ac97460cae', 'snap-0edbbcfc840501fbd', 'snap-03639e3931802e37b',
        'snap-07fa2469aeb6b5726', 'snap-09c53e2fc91b2029e', 'snap-0786906f4c245d040',
        'snap-053cbd4c17d984d52', 'snap-0de3b7913527ee99e', 'snap-0f9c6458a087518eb',
        'snap-093ef77d468014b60', 'snap-0c792fd09b481a767', 'snap-0798bc0d4f9d88dab',
        'snap-08956a944114a2666', 'snap-0bf37f40102486722', 'snap-0a30dc6cb7947c248',
        'snap-033396f6507a47636'
    ]
    
    delete_snapshots(profile_name, snapshots_to_delete)

if __name__ == "__main__":
    main()

