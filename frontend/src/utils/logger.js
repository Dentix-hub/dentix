const isProd = typeof import.meta !== "undefined" && import.meta.env?.PROD;

export const logger = {
  debug: (...args) => !isProd && console.debug(...args),
  log: (...args) => !isProd && console.log(...args),
  info: (...args) => !isProd && console.info(...args),
  warn: (...args) => !isProd && console.warn(...args),
  error: (...args) => !isProd && console.error(...args),
};

export default logger;
