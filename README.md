<!DOCTYPE html>
<html lang="en">
<head>
</head>
<body>

    <h1>Fleet Management System</h1>

    <h2>Project Description</h2>
    <p>
        The Fleet Management System is a web application designed to manage vehicle fleets and their associated documents efficiently. Users can register, log in, add vehicles, and manage documents such as insurance and permits. The system provides automated email notifications to remind users of document expirations, ensuring timely renewals.
    </p>

    <h2>Current Progress</h2>
    <p>
        So far, user authentication, vehicle management, and document management features have been implemented. Email notifications are set up to alert users 10 days before document expiration. A scheduler (APScheduler) runs daily to check for expiring documents and send reminders. Future work involves integrating SMS notifications via Twilio and refining the user interface.
    </p>

</body>
</html>
