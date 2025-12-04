# CertifyPro: Dynamic Certificate Generator

#### Video Demo:  <URL HERE>

#### Description:

CertifyPro is a web-based application designed to streamline the process of creating, managing, and distributing personalized certificates. Whether for a workshop, a course completion, or an award, this tool allows you to generate professional-looking certificates for multiple participants with just a few clicks.

##### How to Use It:

1.  **Add Participants**: You can add participants in two ways:
    *   **Manual Entry**: Go to the "Upload Participants" page and use the "Add Single Participant" form to add individuals one by one. You can also add custom fields for extra information.
    *   **CSV Upload**: On the same page, you can upload a CSV file containing participant data. The only required column is 'name', but you can also include 'email', 'event', 'date', 'position', and any other custom fields you need.

2.  **Manage Templates**:
    *   Go to the "Manage Templates" page to upload your own certificate background images (in PNG or JPG format).
    *   For each template, you must provide a JSON configuration that tells the application where to place the text fields (like 'name', 'date', etc.) on the certificate. You can specify the `x` and `y` coordinates, font size, color, font file, and text alignment (`"align": "center"`).

3.  **Generate Certificates**:
    *   Navigate to the "Generate Certificates" page.
    *   Select the participants you want to create certificates for from the list.
    *   Choose the desired certificate template.
    *   Click "Generate Selected Certificates".

4.  **View and Download**:
    *   On the "View Certificates" page, you will see a gallery of all the certificates you have generated.
    *   From here, you can download each certificate as a PNG or PDF file, or delete them if needed.

This application simplifies certificate generation by separating participant data from the design templates, making it easy to produce a large number of customized certificates efficiently.
