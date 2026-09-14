import os
import re
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

root = Path(__file__).resolve().parents[1]
os.environ['VEHICLE_MANAGER_DATABASE_URI'] = 'sqlite:///:memory:'
sys.path.insert(0, str(root / 'Python'))
from app import FuelEntry, ServiceHistoryEntry, User, Vehicle, app, db

with app.app_context():
    admin = User(name='Admin', email='preview@example.test', passwordHash='unused', role='admin', isAdmin=True)
    car = Vehicle(brand='BMW', model='E46 Coupé', vin='VORSCHAU', licensePlate='W 123 AB', fuel='Benzin')
    db.session.add_all([admin, car])
    db.session.flush()
    db.session.add(ServiceHistoryEntry(vehicle=car, date=date(2025,8,15), mileage=216088, categories=['purchase'], works=[], description='Fahrzeugkauf'))
    for day, liters, km, price, full in [
        ('2025-09-08','23.09',216542,'33.67',True),
        ('2025-09-14','28.48',216867,'43.26',True),
        ('2025-09-14','33.21',217289,'47.99',True),
        ('2025-09-27','12.11',None,'17.70',False),
        ('2025-10-01','59.66',218065,'89.25',True),
        ('2025-10-05','18.21',None,None,False),
    ]:
        db.session.add(FuelEntry(vehicle=car,date=date.fromisoformat(day),liters=Decimal(liters),mileage=km,price=Decimal(price) if price else None,isFullTank=full))
    db.session.commit()
    client = app.test_client()
    with client.session_transaction() as session:
        session['userId'] = admin.id
    for name, url in [('fuel-preview',f'/vehicle/{car.id}'),('fuel-form-preview',f'/vehicle/{car.id}/fuel/add')]:
        response = client.get(url)
        assert response.status_code == 200, response.status_code
        html = response.get_data(as_text=True)
        html = html.replace('/static/', (root / 'Python' / 'static').as_uri() + '/')
        html = re.sub(r'<img\b[^>]*>', '', html)
        (root / '.cache' / (name + '.html')).write_text(html, encoding='utf-8')
    print('Two rendered previews created using an isolated in-memory database.')
