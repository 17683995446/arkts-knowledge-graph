/**
 * 循环导入链 1, 文件 0
 */

import { Class1 } from './CircularChain1_1';

export class Class0 {
    use1() {
        return new Class1();
    }
}
