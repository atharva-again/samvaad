const { getDefaultConfig } = require("expo/metro-config");
const { withNativeWind } = require("nativewind/metro");
const path = require("path");

const config = getDefaultConfig(__dirname);

config.resolver.unstable_enablePackageExports = true;

config.resolver.extraNodeModules = {
  "react-native-css-interop/jsx-runtime": path.resolve(
    __dirname,
    "node_modules/react-native-css-interop/dist/runtime/jsx-runtime"
  ),
};

module.exports = withNativeWind(config, { input: "./global.css" });
