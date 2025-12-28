/**
 * Face Login System - Camera Utilities
 * Webcam capture and face detection UI helpers
 */

class FaceCamera {
    constructor(options = {}) {
        this.videoElement = options.video || document.getElementById('video');
        this.canvasElement = options.canvas || document.getElementById('canvas');
        this.stream = null;
        this.isActive = false;
        
        this.constraints = {
            video: {
                facingMode: options.facingMode || 'user',
                width: { ideal: options.width || 640 },
                height: { ideal: options.height || 480 }
            },
            audio: false
        };
    }
    
    async start() {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia(this.constraints);
            this.videoElement.srcObject = this.stream;
            this.isActive = true;
            return true;
        } catch (error) {
            console.error('Camera error:', error);
            throw new Error('Could not access camera: ' + error.message);
        }
    }
    
    stop() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
            this.isActive = false;
        }
    }
    
    capture(format = 'image/jpeg', quality = 0.9) {
        if (!this.isActive) {
            throw new Error('Camera not active');
        }
        
        this.canvasElement.width = this.videoElement.videoWidth;
        this.canvasElement.height = this.videoElement.videoHeight;
        
        const ctx = this.canvasElement.getContext('2d');
        ctx.drawImage(this.videoElement, 0, 0);
        
        return this.canvasElement.toDataURL(format, quality);
    }
    
    captureBlob(format = 'image/jpeg', quality = 0.9) {
        return new Promise((resolve) => {
            this.canvasElement.width = this.videoElement.videoWidth;
            this.canvasElement.height = this.videoElement.videoHeight;
            
            const ctx = this.canvasElement.getContext('2d');
            ctx.drawImage(this.videoElement, 0, 0);
            
            this.canvasElement.toBlob(resolve, format, quality);
        });
    }
}

// API Helper
class FaceLoginAPI {
    constructor(baseUrl = '') {
        this.baseUrl = baseUrl;
        this.token = localStorage.getItem('token');
    }
    
    async request(endpoint, options = {}) {
        const url = this.baseUrl + endpoint;
        
        options.headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };
        
        if (this.token) {
            options.headers['Authorization'] = `Bearer ${this.token}`;
        }
        
        const response = await fetch(url, options);
        const data = await response.json();
        
        if (response.status === 401) {
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            window.location.href = '/login';
        }
        
        return { response, data };
    }
    
    async loginWithFace(imageData) {
        return this.request('/api/login/face', {
            method: 'POST',
            body: JSON.stringify({ face_image: imageData })
        });
    }
    
    async loginWithPassword(username, password) {
        return this.request('/api/login/password', {
            method: 'POST',
            body: JSON.stringify({ username, password })
        });
    }
    
    async register(userData) {
        return this.request('/api/register', {
            method: 'POST',
            body: JSON.stringify(userData)
        });
    }
    
    async logout() {
        return this.request('/api/logout', { method: 'POST' });
    }
    
    async getMe() {
        return this.request('/api/me');
    }
    
    async getAttendance(limit = 50) {
        return this.request(`/api/attendance?limit=${limit}`);
    }
    
    async getStats() {
        return this.request('/api/stats');
    }
    
    async getUsers() {
        return this.request('/api/users');
    }
    
    async deleteUser(userId) {
        return this.request(`/api/users/${userId}`, { method: 'DELETE' });
    }
}

// Export for use
window.FaceCamera = FaceCamera;
window.FaceLoginAPI = FaceLoginAPI;
