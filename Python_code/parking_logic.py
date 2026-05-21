import database


def handle_entry_logic(car_id):
    """处理入场逻辑"""
    if database.get_available_spots() <= 0:
        return False, "Full"
    if database.is_car_parked(car_id):
        return False, "Already In"

    database.start_session(car_id)
    return True, "Welcome"


def handle_exit_logic(car_id):
    """处理出场扣款逻辑"""
    if not database.is_car_parked(car_id):
        return False, "Not In System"

    fee = database.calculate_current_fee(car_id)
    if database.deduct_fee(car_id, fee):
        database.complete_exit(car_id, fee)
        return True, f"Paid {fee}"
    else:
        return False, "Low Balance"