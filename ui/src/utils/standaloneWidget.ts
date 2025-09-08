
export const generateStandaloneWidget = (apiUrl: string, defaultLanguage?: string): string => {
    const translations = {
        no: {
            check: "Sjekk",
            phoneInputHelper: "Skriv inn ditt 8-sifrede norske telefonnummer for å finne din adresse automatisk.",
            phoneNumberPlaceholder: "12345678",
            phoneValidationError: "Telefonnummeret må være 8 siffer.",
            addressFound: "Adresse funnet! Oppdaterer leveringsvalg...",
            timeoutError: "Forespørselen tok for lang tid. Prøv igjen eller skriv inn adressen manuelt.",
            lookupFailed: "Kunne ikke finne adresse for dette telefonnummeret.",
            manualEntryPrompt: "Vennligst fyll inn adressen manuelt.",
            manualEntryTitle: "Fyll inn adresse manuelt",
            deliveryCheckFailed: "Kunne ikke hente leveringsalternativer.",
            deliveryUnavailable: "Ingen levering tilgjengelig for dette postnummeret."
        },
        en: {
            check: "Check",
            phoneInputHelper: "Enter your 8-digit Norwegian phone number to automatically find your address.",
            phoneNumberPlaceholder: "12345678",
            phoneValidationError: "Phone number must be 8 digits.",
            addressFound: "Address found! Updating delivery options...",
            timeoutError: "Request took too long. Please try again or enter the address manually.",
            lookupFailed: "Could not find address for this phone number.",
            manualEntryPrompt: "Please enter the address manually.",
            manualEntryTitle: "Enter Address Manually",
            deliveryCheckFailed: "Failed to fetch delivery options.",
            deliveryUnavailable: "No delivery available for this postal code."
        }
    };

    // Auto-detect language or use optional override
    const detected = (typeof navigator !== 'undefined' && navigator.language ? navigator.language : '');
    const lang = defaultLanguage || (detected.startsWith('no') ? 'no' : 'en');
    const translation = translations[lang];

    return `<!DOCTYPE html>
<html lang="${lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DeliverEase Widget</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        body {
            font-family: 'Poppins', sans-serif;
            color: #5d5c45;
            line-height: 1.6;
            padding: 20px;
            background: #f8f9fa;
        }
        
        .widget-container {
            max-width: 600px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            padding: 32px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            border: 1px solid #e5e7eb;
        }
        
        .widget-header {
            text-align: center;
            margin-bottom: 24px;
        }
        
        .widget-title {
            font-size: 24px;
            font-weight: 600;
            color: #5d5c45;
            margin-bottom: 8px;
        }
        
        .widget-subtitle {
            color: #6b7280;
            font-size: 16px;
        }
        
        .form-container {
            margin-top: 24px;
        }
        
        .input-group {
            display: flex;
            gap: 8px;
            margin-bottom: 12px;
        }
        
        .country-prefix {
            display: flex;
            align-items: center;
            padding: 12px 16px;
            background: #f3f4f6;
            border: 1px solid #d1d5db;
            border-radius: 8px;
            font-size: 14px;
            color: #5d5c45;
            font-weight: 500;
        }
        
        .phone-input {
            flex: 1;
            padding: 12px 16px;
            border: 1px solid #d1d5db;
            border-radius: 8px;
            font-size: 16px;
            font-family: 'Poppins', sans-serif;
            transition: border-color 0.2s;
        }
        
        .phone-input:focus {
            outline: none;
            border-color: #5d5c45;
            box-shadow: 0 0 0 2px rgba(93, 92, 69, 0.1);
        }
        
        .check-button {
            padding: 12px 24px;
            background: #5d5c45;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 500;
            cursor: pointer;
            transition: background-color 0.2s;
            font-family: 'Poppins', sans-serif;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .check-button:hover:not(:disabled) {
            background: #4a4937;
        }
        
        .check-button:disabled {
            background: #9ca3af;
            cursor: not-allowed;
        }
        
        .loading-spinner {
            width: 16px;
            height: 16px;
            border: 2px solid #ffffff;
            border-top: 2px solid transparent;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .error-message {
            color: #ef4444;
            font-size: 14px;
            margin-top: 8px;
        }
        
        .helper-text {
            color: #6b7280;
            font-size: 12px;
            margin-top: 8px;
        }
        
        .toast {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 16px 24px;
            border-radius: 8px;
            color: white;
            font-weight: 500;
            opacity: 0;
            transform: translateX(100%);
            transition: all 0.3s ease;
            z-index: 10001;
            max-width: 400px;
            word-wrap: break-word;
        }
        
        .toast.show {
            opacity: 1;
            transform: translateX(0);
        }
        
        .toast:not(.error) {
            background: #10b981;
        }
        
        .toast.error {
            background: #ef4444;
        }
    </style>
</head>
<body>
    <div class="widget-container">
        <div class="widget-header">
            <h1 class="widget-title">DeliverEase</h1>
            <p class="widget-subtitle">Check delivery options for your address</p>
        </div>
        
        <div class="form-container">
            <form id="phoneForm">
                <div class="input-group">
                    <div class="country-prefix">+47</div>
                    <input 
                        type="tel" 
                        id="phoneNumber" 
                        class="phone-input"
                        placeholder="${translation.phoneNumberPlaceholder}"
                        maxlength="8"
                        oninput="handlePhoneChange(this.value)"
                    />
                    <button type="submit" class="check-button" id="checkButton">
                        <span id="buttonText">${translation.check}</span>
                        <div id="loadingSpinner" class="loading-spinner" style="display: none;"></div>
                    </button>
                </div>
                <div id="errorMessage" class="error-message" style="display: none;"></div>
                <div class="helper-text">${translation.phoneInputHelper}</div>
            </form>
        </div>
    </div>
    
    <div id="toast" class="toast"></div>

    <script>
        const API_URL = '${apiUrl}';
        const TRANSLATIONS = ${JSON.stringify(translation)};
        
        let phoneNumber = '';
        let isLoading = false;
        
        function validatePhoneNumber(number) {
            const norwegianPhoneRegex = /^\\d{8}$/;
            return norwegianPhoneRegex.test(number);
        }
        
        function handlePhoneChange(value) {
            // Sanitize input: remove spaces, dashes, and other non-numeric characters
            const sanitized = value.replace(/[^0-9]/g, '');
            phoneNumber = sanitized;
            
            // Update the input field to show sanitized value
            const input = document.getElementById('phoneNumber');
            if (input && input.value !== sanitized) {
                input.value = sanitized;
            }
            
            const isValid = validatePhoneNumber(sanitized);
            const hasValue = sanitized.length > 0;
            
            const errorEl = document.getElementById('errorMessage');
            const button = document.getElementById('checkButton');
            
            if (hasValue && !isValid) {
                errorEl.textContent = TRANSLATIONS.phoneValidationError;
                errorEl.style.display = 'block';
            } else {
                errorEl.style.display = 'none';
            }
            
            button.disabled = !isValid || isLoading;
        }
        
        function showToast(message, isError = false) {
            const toast = document.getElementById('toast');
            toast.textContent = message;
            toast.className = 'toast show' + (isError ? ' error' : '');
            
            setTimeout(() => {
                toast.className = 'toast';
            }, 3000);
        }
        
        function setLoading(loading) {
            isLoading = loading;
            const button = document.getElementById('checkButton');
            const buttonText = document.getElementById('buttonText');
            const spinner = document.getElementById('loadingSpinner');
            const input = document.getElementById('phoneNumber');
            
            if (loading) {
                buttonText.style.display = 'none';
                spinner.style.display = 'block';
                button.disabled = true;
                input.disabled = true;
            } else {
                buttonText.style.display = 'block';
                spinner.style.display = 'none';
                button.disabled = !validatePhoneNumber(phoneNumber);
                input.disabled = false;
            }
        }
        
        async function callWithTimeout(promise, timeoutMs) {
            let timeoutHandle;
            
            const timeoutPromise = new Promise((_, reject) => {
                timeoutHandle = setTimeout(
                    () => reject(new Error('ApiTimeoutError')),
                    timeoutMs
                );
            });
            
            try {
                const result = await Promise.race([promise, timeoutPromise]);
                clearTimeout(timeoutHandle);
                return result;
            } catch (error) {
                clearTimeout(timeoutHandle);
                throw error;
            }
        }
        
        function showManualEntryPopup(errorMessage) {
            // Create modal overlay
            const overlay = document.createElement('div');
            overlay.id = 'manual-entry-overlay';
            overlay.style.cssText = \`
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.5);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 10000;
            \`;
            
            // Create modal content
            const modal = document.createElement('div');
            modal.style.cssText = \`
                background: white;
                padding: 24px;
                border-radius: 8px;
                max-width: 500px;
                width: 90%;
                max-height: 80vh;
                overflow-y: auto;
                box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
            \`;
            
            modal.innerHTML = \`
                <h2 style="margin: 0 0 16px 0; color: #5d5c45; font-family: Poppins, sans-serif; font-size: 20px;">
                    \${TRANSLATIONS.manualEntryTitle || 'Enter Address Manually'}
                </h2>
                <p style="margin: 0 0 20px 0; color: #666; font-family: Poppins, sans-serif;">
                    \${errorMessage}
                </p>
                <form id="manual-address-form" style="display: grid; gap: 16px;">
                    <div>
                        <label style="display: block; margin-bottom: 4px; color: #5d5c45; font-family: Poppins, sans-serif; font-weight: 500;">Phone Number</label>
                        <input type="tel" id="manual-phone" value="\${phoneNumber}" readonly style="width: 100%; padding: 8px 12px; border: 1px solid #ccc; border-radius: 4px; font-family: Poppins, sans-serif; background: #f5f5f5;" />
                    </div>
                    <div>
                        <label style="display: block; margin-bottom: 4px; color: #5d5c45; font-family: Poppins, sans-serif; font-weight: 500;">Full Name</label>
                        <input type="text" id="manual-name" required style="width: 100%; padding: 8px 12px; border: 1px solid #ccc; border-radius: 4px; font-family: Poppins, sans-serif;" />
                    </div>
                    <div>
                        <label style="display: block; margin-bottom: 4px; color: #5d5c45; font-family: Poppins, sans-serif; font-weight: 500;">Address</label>
                        <input type="text" id="manual-address" required style="width: 100%; padding: 8px 12px; border: 1px solid #ccc; border-radius: 4px; font-family: Poppins, sans-serif;" />
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 2fr; gap: 12px;">
                        <div>
                            <label style="display: block; margin-bottom: 4px; color: #5d5c45; font-family: Poppins, sans-serif; font-weight: 500;">Postal Code</label>
                            <input type="text" id="manual-postal" required style="width: 100%; padding: 8px 12px; border: 1px solid #ccc; border-radius: 4px; font-family: Poppins, sans-serif;" />
                        </div>
                        <div>
                            <label style="display: block; margin-bottom: 4px; color: #5d5c45; font-family: Poppins, sans-serif; font-weight: 500;">City</label>
                            <input type="text" id="manual-city" required style="width: 100%; padding: 8px 12px; border: 1px solid #ccc; border-radius: 4px; font-family: Poppins, sans-serif;" />
                        </div>
                    </div>
                    <div style="display: flex; gap: 12px; margin-top: 16px;">
                        <button type="button" onclick="closeManualEntryPopup()" style="flex: 1; padding: 10px; border: 1px solid #ddd; background: white; color: #666; border-radius: 4px; cursor: pointer; font-family: Poppins, sans-serif;">
                            Cancel
                        </button>
                        <button type="submit" style="flex: 1; padding: 10px; border: none; background: #5d5c45; color: white; border-radius: 4px; cursor: pointer; font-family: Poppins, sans-serif;">
                            Submit
                        </button>
                    </div>
                </form>
            \`;
            
            overlay.appendChild(modal);
            document.body.appendChild(overlay);
            
            // Handle form submission
            document.getElementById('manual-address-form').addEventListener('submit', function(e) {
                e.preventDefault();
                
                const manualData = {
                    phoneNumber: document.getElementById('manual-phone').value,
                    firstName: document.getElementById('manual-name').value.split(' ')[0] || '',
                    lastName: document.getElementById('manual-name').value.split(' ').slice(1).join(' ') || '',
                    address: document.getElementById('manual-address').value,
                    postalCode: document.getElementById('manual-postal').value,
                    city: document.getElementById('manual-city').value
                };
                
                // Send to parent window if embedded
                if (window.parent && window.parent !== window) {
                    window.parent.postMessage({
                        type: 'deliverease-manual-data',
                        data: manualData
                    }, '*');
                }
                
                closeManualEntryPopup();
                showToast('Address information submitted successfully!');
            });
            
            // Close on overlay click
            overlay.addEventListener('click', function(e) {
                if (e.target === overlay) {
                    closeManualEntryPopup();
                }
            });
        }
        
        function closeManualEntryPopup() {
            const overlay = document.getElementById('manual-entry-overlay');
            if (overlay) {
                overlay.remove();
            }
        }
        
        async function handleSubmit(event) {
            event.preventDefault();
            
            if (!validatePhoneNumber(phoneNumber) || isLoading) {
                return;
            }
            
            setLoading(true);
            
            try {
                const response = await callWithTimeout(
                    fetch(API_URL + '/addresslookup/address', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ phone_number: phoneNumber })
                    }),
                    8000
                );
                
                // Handle rate limiting (429) or service unavailable (503) gracefully
                if (response.status === 429 || response.status === 503) {
                    console.log('API rate limited or unavailable, showing manual entry');
                    
                    const rateLimitMessage = 'Address lookup service is temporarily busy. Please enter your address manually.';
                    
                    if (window.parent && window.parent !== window) {
                        window.parent.postMessage({
                            type: 'deliverease-open-popup',
                            data: {
                                phoneNumber: phoneNumber,
                                manualEntry: true,
                                error: rateLimitMessage
                            }
                        }, '*');
                    } else {
                        showManualEntryPopup(rateLimitMessage);
                    }
                    
                    return; // Skip the error throwing
                }
                
                if (!response.ok) {
                    throw new Error('Address lookup failed');
                }
                
                const addressData = await response.json();
                
                // Send data to parent page to open popup
                if (window.parent && window.parent !== window) {
                    window.parent.postMessage({
                        type: 'deliverease-open-popup',
                        data: {
                            phoneNumber: phoneNumber,
                            address: addressData
                        }
                    }, '*');
                }
                
                // Reset form and show success
                document.getElementById('phoneNumber').value = '';
                phoneNumber = '';
                handlePhoneChange('');
                showToast(TRANSLATIONS.addressFound);
                
            } catch (error) {
                console.error('Phone lookup error:', error);
                
                let errorMessage;
                
                if (error.message === 'ApiTimeoutError') {
                    errorMessage = TRANSLATIONS.timeoutError;
                } else {
                    errorMessage = TRANSLATIONS.lookupFailed;
                }
                
                // Send manual entry request to popup
                if (window.parent && window.parent !== window) {
                    window.parent.postMessage({
                        type: 'deliverease-open-popup',
                        data: {
                            phoneNumber: phoneNumber,
                            manualEntry: true,
                            error: errorMessage
                        }
                    }, '*');
                } else {
                    // Standalone mode: create and show manual entry popup
                    showManualEntryPopup(errorMessage);
                }
                
            } finally {
                setLoading(false);
            }
        }
        
        // Add paste event listener to sanitize pasted content
        document.addEventListener('DOMContentLoaded', function() {
            const phoneInput = document.getElementById('phoneNumber');
            if (phoneInput) {
                phoneInput.addEventListener('paste', function(e) {
                    setTimeout(() => {
                        const value = e.target.value;
                        const sanitized = value.replace(/[^0-9]/g, '');
                        if (value !== sanitized) {
                            e.target.value = sanitized;
                            handlePhoneChange(sanitized);
                        }
                    }, 0);
                });
            }
        });
        
        // Initialize
        document.getElementById('phoneForm').addEventListener('submit', handleSubmit);
        document.getElementById('checkButton').disabled = true;
    </script>
</body>
</html>`;
};
