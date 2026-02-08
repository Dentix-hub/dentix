import { toast } from 'react-hot-toast';

export const showToast = (type, message) => {
    switch (type) {
        case 'success':
            toast.success(message);
            break;
        case 'error':
            toast.error(message);
            break;
        case 'loading':
            toast.loading(message);
            break;
        default:
            toast(message);
    }
};

export { toast };
export default showToast;
