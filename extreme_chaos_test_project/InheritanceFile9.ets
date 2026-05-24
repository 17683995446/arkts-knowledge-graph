/**
 * 继承链文件 - 深度 9
 */

import { InheritanceClass8 } from './InheritanceFile8';

export class InheritanceClass9 extends InheritanceClass8 {

    method0() {
        super.method2?.();
        return 'Inheritance 9 result';
    }


    method1() {
        super.method4?.();
        return 'Inheritance 9 result';
    }


    method2() {
        super.method2?.();
        return 'Inheritance 9 result';
    }


    method3() {
        super.method1?.();
        return 'Inheritance 9 result';
    }


    method4() {
        super.method1?.();
        return 'Inheritance 9 result';
    }


    method5() {
        super.method5?.();
        return 'Inheritance 9 result';
    }

}
