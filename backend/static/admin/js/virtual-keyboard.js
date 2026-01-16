class VirtualKeyboard {
    constructor(inputSelector, options = {}) {
        this.inputElement = document.querySelector(inputSelector);
        if (!this.inputElement) {
            console.error('Input element not found:', inputSelector);
            return;
        }
        
        this.options = {
            maxLength: options.maxLength || 6,
            shuffle: options.shuffle || false,
            onComplete: options.onComplete || null
        };
        
        this.currentValue = '';
        this.createKeyboard();
    }
    
    createKeyboard() {
        // Create keyboard container
        this.keyboardContainer = document.createElement('div');
        this.keyboardContainer.className = 'virtual-keyboard';
        
        // Create display
        this.display = document.createElement('div');
        this.display.className = 'keyboard-display';
        this.updateDisplay();
        this.keyboardContainer.appendChild(this.display);
        
        // Create keys
        let keysContainer = document.createElement('div');
        keysContainer.className = 'keyboard-keys';
        
        let digits = [1, 2, 3, 4, 5, 6, 7, 8, 9, 0];
        if (this.options.shuffle) {
            digits = this.shuffleArray(digits);
        }
        
        // Add number keys
        digits.forEach(digit => {
            let key = document.createElement('button');
            key.type = 'button';
            key.className = 'keyboard-key';
            key.textContent = digit;
            key.addEventListener('click', () => this.addDigit(digit));
            keysContainer.appendChild(key);
        });
        
        // Add backspace key
        let backspaceKey = document.createElement('button');
        backspaceKey.type = 'button';
        backspaceKey.className = 'keyboard-key keyboard-key-wide';
        backspaceKey.innerHTML = 'Backspace';
        backspaceKey.addEventListener('click', () => this.removeDigit());
        keysContainer.appendChild(backspaceKey);
        
        // Add clear key
        let clearKey = document.createElement('button');
        clearKey.type = 'button';
        clearKey.className = 'keyboard-key keyboard-key-wide';
        clearKey.innerHTML = 'Clear';
        clearKey.addEventListener('click', () => this.clearInput());
        keysContainer.appendChild(clearKey);
        
        this.keyboardContainer.appendChild(keysContainer);
        
        // Add keyboard after the input element
        this.inputElement.parentNode.insertBefore(this.keyboardContainer, this.inputElement.nextSibling);
        
        // Hide the original input
        this.inputElement.style.display = 'none';
    }
    
    addDigit(digit) {
        if (this.currentValue.length < this.options.maxLength) {
            this.currentValue += digit;
            this.inputElement.value = this.currentValue;
            this.updateDisplay();
            
            if (this.currentValue.length === this.options.maxLength && this.options.onComplete) {
                this.options.onComplete(this.currentValue);
            }
        }
    }
    
    removeDigit() {
        if (this.currentValue.length > 0) {
            this.currentValue = this.currentValue.slice(0, -1);
            this.inputElement.value = this.currentValue;
            this.updateDisplay();
        }
    }
    
    clearInput() {
        this.currentValue = '';
        this.inputElement.value = '';
        this.updateDisplay();
    }
    
    updateDisplay() {
        // Clear the display
        this.display.innerHTML = '';
        
        // Create dots for each possible digit
        for (let i = 0; i < this.options.maxLength; i++) {
            let dot = document.createElement('div');
            dot.className = 'keyboard-dot';
            
            // Fill the dot if we have a digit at this position
            if (i < this.currentValue.length) {
                dot.classList.add('keyboard-dot-filled');
            }
            
            this.display.appendChild(dot);
        }
    }
    
    shuffleArray(array) {
        // Create a copy to avoid modifying the original
        let newArray = [...array];
        for (let i = newArray.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [newArray[i], newArray[j]] = [newArray[j], newArray[i]];
        }
        return newArray;
    }
}