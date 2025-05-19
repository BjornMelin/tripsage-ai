/**
 * TripSage Database Connection Verification Script
 *
 * This script verifies the connection to the Supabase database
 * and checks that the required tables exist.
 *
 * Usage: node verify_connection.js
 */

const { createClient } = require("@supabase/supabase-js");
require("dotenv").config();

// Check for required environment variables
const supabaseUrl = process.env.SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseKey) {
  console.error(
    "ERROR: Missing environment variables SUPABASE_URL and/or SUPABASE_ANON_KEY"
  );
  console.error(
    "Please create a .env file based on .env.example and add your Supabase credentials"
  );
  process.exit(1);
}

// Create Supabase client
const supabase = createClient(supabaseUrl, supabaseKey);

// Tables that should exist
const requiredTables = [
  "users",
  "trips",
  "flights",
  "accommodations",
  "transportation",
  "itinerary_items",
  "search_parameters",
  "price_history",
  "trip_notes",
  "saved_options",
  "trip_comparison",
];

// Verify connection and tables
async function verifyConnection() {
  console.log("Connecting to Supabase at:", supabaseUrl);

  try {
    // Test a simple query to verify connection
    const { data, error } = await supabase.from("trips").select("id").limit(1);

    if (error) throw error;

    console.log("✅ Successfully connected to Supabase!");

    // Verify tables
    console.log("\nChecking required tables:");

    // Get list of tables using system schema
    const { data: tables, error: tablesError } = await supabase.rpc(
      "get_tables"
    );

    if (tablesError) {
      console.log(
        "Unable to list tables using RPC. Using alternative method..."
      );

      // Alternative method to check tables individually
      for (const table of requiredTables) {
        try {
          const { data, error } = await supabase
            .from(table)
            .select("id")
            .limit(1);

          if (error && error.code === "42P01") {
            console.log(`❌ Table '${table}' does not exist`);
          } else {
            console.log(`✅ Table '${table}' exists`);
          }
        } catch (err) {
          console.log(`❓ Could not verify table '${table}': ${err.message}`);
        }
      }

      return;
    }

    // If we have table list, check required tables
    const tableNames = tables.map((t) => t.table_name);

    for (const table of requiredTables) {
      if (tableNames.includes(table)) {
        console.log(`✅ Table '${table}' exists`);
      } else {
        console.log(`❌ Table '${table}' does not exist`);
      }
    }

    console.log("\nDatabase verification complete!");
  } catch (err) {
    console.error("❌ Error connecting to Supabase:", err.message);
    process.exit(1);
  }
}

// Run the verification
verifyConnection();
