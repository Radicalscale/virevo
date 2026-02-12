const { MongoClient } = require('mongodb');

const SOURCE_URI = 'mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada';

async function listAllUsers() {
    const client = new MongoClient(SOURCE_URI);
    try {
        await client.connect();
        const db = client.db('test_database');
        const users = await db.collection('users').find({}).toArray();

        console.log(`\n--- All Users in 'test_database' (${users.length}) ---`);
        users.forEach((u, index) => {
            console.log(`${index + 1}. ${u.email} [${u.name || 'No Name'}] (ID: ${u._id})`);
        });

    } catch (err) {
        console.error(err);
    } finally {
        await client.close();
    }
}

listAllUsers();
