<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Fleet Management System README</title>
</head>
<body>

<h1>Fleet Management System</h1>

<h2>Project Description</h2>
<p>
  The Fleet Management System is a comprehensive web application designed to manage vehicle fleets and their associated documents efficiently. Users can register, log in, add vehicles, and manage documents such as insurance, permits, and more. The system provides automated email notifications to remind users of document expirations, ensuring timely renewals.
</p>

<h2>Current Progress</h2>
<p>
  <strong>Implemented Features:</strong>
</p>
<ul>
  <li><strong>User Authentication:</strong> Users can register, log in, and log out securely.</li>
  <li><strong>Vehicle Management:</strong> Users can add, edit, delete, and view their vehicles.</li>
  <li><strong>Document Management:</strong> Users can manage documents associated with their vehicles, including types such as insurance, emission certificates, permits, fitness certificates, and road tax receipts.</li>
  <li><strong>Email Notifications:</strong> Automated email notifications alert users 10 days before document expiration.</li>
  <li><strong>Scheduler (APScheduler):</strong> A daily scheduler runs to check for expiring documents and send reminders.</li>
  <li><strong>OTP Verification:</strong> OTP (One-Time Password) verification implemented for critical operations like account deletion and vehicle deletions to enhance security.</li>
  <li><strong>Enhanced Logging:</strong> Comprehensive logging for actions and system events to facilitate monitoring and debugging.</li>
</ul>

<h2>Recent Updates</h2>
<p>
  <strong>Security Enhancements:</strong>
</p>
<ul>
  <li><strong>OTP for Account Deletion:</strong> Users must verify their identity using an OTP sent to their email before account deletion.</li>
  <li><strong>Improved OTP Handling for Vehicle/Document Deletion:</strong> Streamlined OTP verification process to ensure smooth user experience and increased security.</li>
</ul>

<h2>Next Steps</h2>
<p>
  As I continue developing the Fleet Management System, we plan to implement the following features:</p>
<ul>
  <li><strong>Advanced Analytics Dashboard:</strong> Providing users with insights and analytics about their fleet operations.</li>
  <li><strong>Enhanced User Interface:</strong> Improving the user interface to make it more intuitive and user-friendly.</li>
  <li><strong>Integration with External APIs:</strong> Integrating with external APIs for features like VIN lookup, real-time traffic updates, and more.</li>
  <li><strong>Mobile Application:</strong> Developing a companion mobile application for the Fleet Management System.</li>
</ul>

<h2>Contributions</h2>
<p>
  Contributions are WELCOME! Whether through code contributions, bug reports, or feature suggestions.
</p>

</body>
</html>