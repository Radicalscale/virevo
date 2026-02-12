const { MongoClient } = require('mongodb');

const SOURCE_URI = 'mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada';

async function listUsers() {
    const client = new MongoClient(SOURCE_URI);
    try {
        await client.connect();
        // List databases first to be sure
        const adminDb = client.db().admin();
        const dbs = await adminDb.listDatabases();
        console.log("Databases in Cluster:");
        dbs.databases.forEach(db => console.log(` - ${db.name}`));

        const db = client.db('test_database');
        const users = await db.collection('users').find({}).limit(10).toArray();

        console.log("\nSample Users in 'test_database':");
        users.forEach(u => console.log(` - ${u.email} (${u.name || 'No Name'})`));

    } catch (err) {
        console.error(err);
    } finally {
        await client.close();
    }
}

listUsers();
