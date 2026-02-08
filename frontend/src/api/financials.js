import api from './index';

export const getProcedureFinancials = (procedureId) => {
    return api.get(`/api/v1/financials/procedure/${procedureId}/analysis`);
};

export const getAllProceduresFinancials = () => {
    return api.get(`/api/v1/financials/procedures/analysis`);
};
