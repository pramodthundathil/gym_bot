import os
import json
import django
from django.conf import settings

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gym_bot.settings')
django.setup()

from Members.models import MemberData, Subscription, Payment

def verify_data(fixture_path='data_cleaned.json'):
    print(f"Reading fixture: {fixture_path}")
    with open(fixture_path, 'r') as f:
        data = json.load(f)

    # Count records in fixture
    fixture_counts = {
        'Members.memberdata': 0,
        'Members.subscription': 0,
        'Members.payment': 0
    }

    for item in data:
        model = item.get('model')
        if model in fixture_counts:
            fixture_counts[model] += 1

    print("\nFixture Counts:")
    for model, count in fixture_counts.items():
        print(f"  {model}: {count}")

    # Count records in database
    db_counts = {
        'Members.memberdata': MemberData.objects.count(),
        'Members.subscription': Subscription.objects.count(),
        'Members.payment': Payment.objects.count()
    }

    print("\nDatabase Counts:")
    for model, count in db_counts.items():
        print(f"  {model}: {count}")

    # Identify discrepancies
    print("\nDiscrepancies:")
    for model in fixture_counts:
        diff = fixture_counts[model] - db_counts[model]
        if diff > 0:
            print(f"  {model}: {diff} records missing in database")
        elif diff < 0:
            print(f"  {model}: {abs(diff)} extra records in database")
        else:
            print(f"  {model}: All records account for.")

    # Check for dangling subscriptions
    dangling = Subscription.objects.filter(Member__isnull=True).count()
    if dangling > 0:
        print(f"\n[WARNING] {dangling} subscriptions found without a linked member. This will cause NoReverseMatch errors in templates.")

if __name__ == "__main__":
    verify_data()
