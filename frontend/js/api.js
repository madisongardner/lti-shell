const API = {
    async getUserInfo() {
        try {
            const response = await fetch('/api/user-info', {
            credentials: 'same-origin',
        });

        if (!response.ok) {
            if (response.status === 401) return null;
            throw new Error('HTTP ' + response.status);
        }
        return await response.json();


    } catch (error) {
        console.error('Failed to fetch user info:', error);
        return null;
    }
 },
};