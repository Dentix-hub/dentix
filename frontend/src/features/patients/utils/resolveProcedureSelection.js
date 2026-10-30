import logger from '@/utils/logger';

/**
 * Extension point for procedure price resolution and BOM autoload.
 * Note: S30 material suggestion / deduct-at-use will extend this function.
 * This helper is the ONLY place BOM autoload and price resolution live.
 *
 * @param {Object} params
 * @param {string} params.procedureName - Name of the procedure to resolve
 * @param {Array} [params.procedures=[]] - List of available procedure objects
 * @param {string|number|null} [params.defaultPriceListId=null] - Patient's default price list ID
 * @param {string|number|null} [params.currentPriceListId=null] - Current active price list ID on treatment
 * @returns {Promise<{ found: boolean, cost: number, price_list_id: string|number|null, autoMaterials: Array }>}
 */
export async function resolveProcedureSelection({
    procedureName,
    procedures = [],
    defaultPriceListId = null,
    currentPriceListId = null,
}) {
    const safeProcedures = Array.isArray(procedures) ? procedures : [];
    const foundProc = safeProcedures.find((p) => p.name === procedureName);

    if (!foundProc) {
        return {
            found: false,
            cost: 0,
            price_list_id: currentPriceListId,
            autoMaterials: [],
        };
    }

    const baseProcedurePrice = foundProc?.price || 0;
    let calculatedPrice = baseProcedurePrice;
    let activePriceListId = currentPriceListId;

    logger.debug('[PRICE_DEBUG] Found Procedure:', foundProc?.name, 'Base Price:', baseProcedurePrice);
    logger.debug('[PRICE_DEBUG] Default Price List ID:', defaultPriceListId);

    if (foundProc && defaultPriceListId) {
        try {
            // Dynamic import to avoid circular dependency
            const { getProcedurePrices } = await import('@/api');
            const pricesData = await getProcedurePrices(foundProc.id);
            logger.debug('[PRICE_DEBUG] Prices Data:', pricesData?.data);

            const specificPrice = pricesData?.data?.price_lists?.find(
                (pl) => String(pl.price_list_id) === String(defaultPriceListId)
            );
            logger.debug('[PRICE_DEBUG] Specific Price Found:', specificPrice);

            if (specificPrice && specificPrice.final_price > 0) {
                // Use price list price ONLY if it's greater than 0
                calculatedPrice = specificPrice.final_price;
                activePriceListId = defaultPriceListId;
            } else if (specificPrice && specificPrice.final_price === 0) {
                // Price list has 0 - fallback to base procedure price
                logger.debug('[PRICE_DEBUG] Price list price is 0, using base procedure price:', baseProcedurePrice);
                calculatedPrice = baseProcedurePrice;
            }
        } catch (err) {
            logger.error('Failed to fetch custom prices', err);
        }
    }

    logger.debug('[PRICE_DEBUG] Final Calculated Price:', calculatedPrice);

    const autoMaterials = (foundProc.suggestedMaterials || []).map((sm) => ({
        material_id: sm.id,
        quantity: sm.quantity,
        name: sm.name,
        unit: sm.unit,
        is_manual: false,
    }));

    return {
        found: true,
        cost: calculatedPrice,
        price_list_id: activePriceListId,
        autoMaterials,
    };
}
