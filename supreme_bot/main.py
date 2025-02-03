from automate_buy import buy

def main():
    # Chrome profile paths
    chrome_path = r"C:\Users\kaile\AppData\Local\Google\Chrome\User Data"  # Update to your Chrome path
    chrome_profile = r"Profile 5"  # Change this as needed

    # Keywords paired with respective sizes
    items = [
        ['Box Logo Hooded Sweatshirt - Green', 'Large'],
        ['Ushanka Hat', 'One Size'],
    ]

    buy(items)  # Pass the list of item-size pairs

if __name__ == "__main__":
    main()
