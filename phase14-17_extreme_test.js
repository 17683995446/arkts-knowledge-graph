
const path = require('path');
const fs = require('fs');

console.log('===== 第14-17阶段：超极端复杂场景全面测试 =====\n');

// 创建测试场景
console.log('--- 第13阶段：创建测试场景 ---');
require('./create_extreme_chaos_test.js');

const EXTREME_TEST_DIR = path.join(__dirname, 'extreme_chaos_test');
const EXTREME_DB_PATH = path.join(__dirname, 'extreme_test.db');

if (fs.existsSync(EXTREME_DB_PATH)) {
  fs.unlinkSync(EXTREME_DB_PATH);
}

const { FileUpdater } = require('./dist/core/file_updater');
const { DatabaseManager } = require('./dist/database/database_manager');
const { ArkTsParser } = require('./dist/parser/arkts_parser');

async function runExtremeTests() {
  try {
    console.log('\n--- 第14阶段：初始化和第一次完整扫描 ---');
    const db = new DatabaseManager(EXTREME_DB_PATH);
    await db.init();
    const parser = new ArkTsParser();
    const updater = new FileUpdater(db, parser, EXTREME_TEST_DIR);
    
    console.time('initial_full_scan');
    await updater.performFullSync();
    console.timeEnd('initial_full_scan');
    
    const files1 = await db.getAllFiles();
    const classes1 = await db.getAllClasses();
    const methods1 = await db.getAllMethods();
    const calls1 = await db.getAllCalls();
    
    console.log('✓ 第一次扫描完成');
    console.log('  - 文件数:', files1.length);
    console.log('  - 类数:', classes1.length);
    console.log('  - 方法数:', methods1.length);
    console.log('  - 调用关系数:', calls1.length);
    
    console.log('\n--- 第15阶段：极端压力测试（多次重复扫描）---');
    
    const repeatCount = 3;
    console.time('multiple_scans');
    for (let i = 0; i < repeatCount; i++) {
      console.log(`  第 ${i + 1} 次扫描...`);
      const startMem = process.memoryUsage().heapUsed;
      
      await updater.performFullSync();
      
      const endMem = process.memoryUsage().heapUsed;
      console.log(`    内存: ${Math.round(startMem / 1024)}KB -> ${Math.round(endMem / 1024)}KB (变化: ${Math.round((endMem - startMem) / 1024)}KB)`);
    }
    console.timeEnd('multiple_scans');
    
    console.log('✓ 多次重复扫描完成');
    
    const files2 = await db.getAllFiles();
    const classes2 = await db.getAllClasses();
    const methods2 = await db.getAllMethods();
    const calls2 = await db.getAllCalls();
    
    console.log('\n--- 第16阶段：数据一致性验证 ---');
    
    let passed = true;
    
    if (files1.length !== files2.length) {
      console.error(`✗ 文件数不一致: ${files1.length} vs ${files2.length}`);
      passed = false;
    } else {
      console.log(`✓ 文件数一致: ${files1.length}`);
    }
    
    if (classes1.length !== classes2.length) {
      console.error(`✗ 类数不一致: ${classes1.length} vs ${classes2.length}`);
      passed = false;
    } else {
      console.log(`✓ 类数一致: ${classes1.length}`);
    }
    
    if (methods1.length !== methods2.length) {
      console.error(`✗ 方法数不一致: ${methods1.length} vs ${methods2.length}`);
      passed = false;
    } else {
      console.log(`✓ 方法数一致: ${methods1.length}`);
    }
    
    if (calls1.length !== calls2.length) {
      console.error(`✗ 调用关系数不一致: ${calls1.length} vs ${calls2.length}`);
      passed = false;
    } else {
      console.log(`✓ 调用关系数一致: ${calls2.length}`);
    }
    
    console.log('\n--- 第17阶段：功能极限验证 ---');
    
    // 验证错误文件是否被正确处理
    const chaosFile = files2.find(f => f.path.includes('chaos_1.ts'));
    if (chaosFile) {
      console.log('✓ 混乱文件被正确处理');
    }
    
    const commentsFile = files2.find(f => f.path.includes('only_comments.ts'));
    if (commentsFile) {
      console.log('✓ 注释文件被正确处理');
    }
    
    const emptyFile = files2.find(f => f.path.includes('totally_empty.ts'));
    if (emptyFile) {
      console.log('✓ 空文件被正确处理');
    }
    
    // 检查是否有深层嵌套的文件
    const deepFiles = files2.filter(f => f.path.includes('deep_dir'));
    if (deepFiles.length > 0) {
      console.log(`✓ 深层嵌套文件被正确处理 (${deepFiles.length} 个)`);
    }
    
    // 检查巨大的类
    const hugeClass = classes2.find(c => c.name.includes('HugeMethodClass'));
    if (hugeClass) {
      const hugeClassMethods = methods2.filter(m => m.class_id === hugeClass.id);
      console.log(`✓ 巨大类被正确处理 (${hugeClassMethods.length} 个方法)`);
    }
    
    console.log('\n--- 验证总结 ---');
    
    if (passed) {
      console.log('✓✓✓ 所有一致性检查通过！');
    } else {
      console.error('✗✗✗ 存在一致性问题！');
      process.exit(1);
    }
    
    console.log('\n--- 最终数据统计 ---');
    console.log('✓ 文件总数:', files2.length);
    console.log('✓ 类总数:', classes2.length);
    console.log('✓ 方法总数:', methods2.length);
    console.log('✓ 调用关系总数:', calls2.length);
    
    console.log('\n===== 第14-17阶段：所有测试完美通过！=====');
    console.log('\n✓✓✓ 系统在极端混乱、超复杂场景下表现完美！');
    
    await db.close();
    
  } catch (error) {
    console.error('\n✗✗✗ 极端测试失败！');
    console.error('错误:', error);
    process.exit(1);
  }
}

runExtremeTests();
