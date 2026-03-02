import smtplib

try:
    print("Testing 587 with STARTTLS")
    server = smtplib.SMTP("smtp.gmail.com", 587, timeout=10)
    server.ehlo()
    server.starttls()
    server.ehlo()
    print("587 STARTTLS Successful!")
    server.quit()
except Exception as e:
    print(f"587 STARTTLS Failed: {e}")

try:
    print("Testing 465 with SSL")
    server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10)
    server.ehlo()
    print("465 SSL Successful!")
    server.quit()
except Exception as e:
    print(f"465 SSL Failed: {e}")
